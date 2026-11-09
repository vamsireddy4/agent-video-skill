"""
analysis.py - local, model-free analysis that reads EVERY frame and the whole audio track.

Video: one low-resolution ffmpeg pass scores every frame for scene change and motion, finds
fast-motion segments, and picks which frames the AI should look at. Fast segments are turned
into "motion strips" (a short burst of frames in one image) so the agent can see movement.

Audio: loudness over time, silence, loud bursts, sound without speech (likely music or
effects), and per-line tone cues (loudness, pitch, speaking speed) for the transcript.

Only ffmpeg is required; numpy and Pillow make the audio and strip parts work.
"""

from __future__ import annotations

import math
import re
import subprocess
import wave
from pathlib import Path


def _ff_filter_path(p: Path) -> str:
    """Escape a path for use inside an ffmpeg filter argument (Windows drive colons too)."""
    s = str(p).replace("\\", "/")
    return s.replace(":", "\\:").replace("'", "\\'")


def _fmt(t: float) -> str:
    t = max(0, int(round(t)))
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# --------------------------------------------------------------------------- #
# Video: every frame
# --------------------------------------------------------------------------- #

def scan_every_frame(ffmpeg: str, input_args: list[str], start: float, end: float | None,
                     work: Path, timeout: float, log=print) -> dict:
    """Decode every frame once at 160 px grey and record scene-change and motion scores.
    Returns {"t": [...], "scene": [...], "motion": [...], "fps": float, "frames": int}."""
    sc_file, mo_file = work / "_scene.txt", work / "_motion.txt"
    for f in (sc_file, mo_file):
        f.unlink(missing_ok=True)
    vf = ("scale=160:-2,format=yuv444p,"
          "select='gte(scene\\,0)',"
          f"metadata=print:key=lavfi.scene_score:file='{_ff_filter_path(sc_file)}',"
          "tblend=all_mode=difference,signalstats,"
          f"metadata=print:file='{_ff_filter_path(mo_file)}'")
    cmd = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-threads", "0"]
    if start:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += input_args
    if end is not None:
        cmd += ["-t", f"{max(0.1, end - start):.3f}"]
    cmd += ["-an", "-sn", "-vf", vf, "-f", "null", "-"]
    log("Reading every frame (scene changes and motion)...")
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        log("Every-frame scan hit the time limit; using what was read so far.")

    def parse(path: Path, keys: tuple[str, ...], weights: tuple[float, ...]) -> dict[float, float]:
        out: dict[float, float] = {}
        if not path.exists():
            return out
        t = None
        with path.open(errors="ignore") as fh:
            for line in fh:
                if line.startswith("frame:"):
                    m = re.search(r"pts_time:([0-9.]+)", line)
                    t = round(float(m.group(1)) + start, 3) if m else None
                    continue
                if t is None:
                    continue
                for k, w in zip(keys, weights):
                    if line.startswith(k + "="):
                        try:
                            out[t] = out.get(t, 0.0) + w * float(line.split("=", 1)[1])
                        except ValueError:
                            pass
        return out

    scene = parse(sc_file, ("lavfi.scene_score",), (1.0,))
    # motion = mean absolute difference between consecutive frames: brightness plus colour
    motion = parse(mo_file, ("lavfi.signalstats.YAVG", "lavfi.signalstats.UAVG", "lavfi.signalstats.VAVG"),
                   (1.0, 0.75, 0.75))
    for f in (sc_file, mo_file):
        f.unlink(missing_ok=True)
    times = sorted(scene)
    if len(times) < 2:
        return {"t": times, "scene": [scene.get(t, 0.0) for t in times],
                "motion": [motion.get(t, 0.0) for t in times], "fps": 0.0, "frames": len(times)}
    span = times[-1] - times[0]
    fps = (len(times) - 1) / span if span > 0 else 0.0
    return {"t": times, "scene": [scene[t] for t in times],
            "motion": [motion.get(t, 0.0) for t in times], "fps": round(fps, 2), "frames": len(times)}


def _percentile(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (k - lo)


def motion_segments(scan: dict, min_level: float = 0.8, merge_gap: float = 0.6,
                    min_len: float = 0.25, max_segments: int = 8) -> tuple[list[dict], float]:
    """Find stretches of fast motion. Motion = mean absolute grey difference between
    consecutive frames (0-255). Scene cuts are excluded so a cut is not called 'motion'."""
    t, m, sc = scan["t"], scan["motion"], scan["scene"]
    if len(t) < 3:
        return [], 0.0
    base = _percentile(m, 0.5)
    # adaptive: a still slide video has base ~0, a talking head or handheld camera has more
    thr = max(min_level, base * 4 + 0.5)
    # light smoothing over ~3 frames so single-frame noise does not count
    sm = [(m[max(0, i - 1)] + m[i] + m[min(len(m) - 1, i + 1)]) / 3 for i in range(len(m))]
    hot_idx = [i for i in range(len(t)) if sm[i] >= thr and sc[i] < 0.5]
    groups: list[list[int]] = []
    for i in hot_idx:
        if groups and t[i] - t[groups[-1][-1]] <= merge_gap:
            groups[-1].append(i)
        else:
            groups.append([i])
    segs: list[dict] = []
    for g in groups:
        i, j = g[0], g[-1]
        if t[j] - t[i] < min_len:
            continue
        vals = m[i:j + 1]
        peak_k = max(range(i, j + 1), key=lambda k: m[k])
        segs.append({"start": round(t[i], 2), "end": round(t[j], 2), "peak_t": round(t[peak_k], 2),
                     "peak": round(m[peak_k], 2), "mean": round(sum(vals) / len(vals), 2)})
    segs.sort(key=lambda s: s["mean"] * (s["end"] - s["start"] + 0.5), reverse=True)
    segs = sorted(segs[:max_segments], key=lambda s: s["start"])
    for s in segs:
        s["level"] = "very fast" if s["mean"] >= thr * 2 else "fast"
    return segs, round(thr, 2)


def activity_by_window(scan: dict, window: float) -> list[dict]:
    """Average motion per time window, labelled calm / moderate / busy."""
    t, m = scan["t"], scan["motion"]
    if not t:
        return []
    med = max(_percentile(m, 0.5), 0.5)
    out, w0 = [], t[0]
    while w0 <= t[-1]:
        vals = [m[i] for i in range(len(t)) if w0 <= t[i] < w0 + window]
        if vals:
            avg = sum(vals) / len(vals)
            label = "busy" if avg >= med * 4 and avg >= 4 else "moderate" if avg >= med * 1.8 and avg >= 1.5 else "calm"
            out.append({"start": round(w0, 2), "end": round(w0 + window, 2), "motion": round(avg, 2), "label": label})
        w0 += window
    return out


def scene_change_times(scan: dict, threshold: float) -> list[float]:
    return [t for t, s in zip(scan["t"], scan["scene"]) if s >= threshold]


def content_change_times(scan: dict, min_level: float = 0.8) -> list[float]:
    """Instant changes that scene detection misses: a new slide, a new line of code, a changed
    number. They show up as a one-frame spike in the frame-to-frame difference. The returned
    time is just after the change, so the grabbed frame shows the new content."""
    t, m = scan["t"], scan["motion"]
    if len(t) < 3:
        return []
    base = _percentile(m, 0.5)
    level = max(min_level, base * 6 + 0.5)
    out = []
    for i in range(1, len(t) - 1):
        nb = max(m[i - 1], m[i + 1])
        if m[i] >= level and m[i] >= 4 * nb:
            out.append(round(t[i] + min(0.15, (t[i + 1] - t[i]) * 2), 3))
    return out


def burst_frames(ffmpeg: str, input_args_at, seg: dict, out_dir: Path, idx: int, fps: float = 8.0,
                 max_frames: int = 12, width: int = 480, timeout: float = 180) -> list[dict]:
    """Grab a short burst of frames covering one fast-motion segment in a single request."""
    pad = 0.25
    s0 = max(0.0, seg["start"] - pad)
    dur = (seg["end"] + pad) - s0
    rate = min(fps, max_frames / max(dur, 0.1))
    pattern = out_dir / f"_burst{idx:02d}_%03d.jpg"
    cmd = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{s0:.3f}"]
    cmd += input_args_at
    cmd += ["-t", f"{dur:.3f}", "-an", "-sn", "-vf", f"fps={rate:.3f},scale='min({width},iw)':-2",
            "-frames:v", str(max_frames), "-q:v", "4", str(pattern)]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        pass
    files = sorted(out_dir.glob(f"_burst{idx:02d}_*.jpg"))
    return [{"t": round(s0 + k / rate, 2), "file": f} for k, f in enumerate(files)]


def make_motion_strip(burst: list[dict], seg: dict, out_file: Path) -> Path | None:
    """Put a burst of frames side by side (2 rows) with timestamps, oldest first."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    if not burst:
        return None
    ims = [Image.open(b["file"]).convert("RGB") for b in burst]
    tw = 320
    ims = [im.resize((tw, max(1, int(im.height * tw / im.width)))) for im in ims]
    th = max(im.height for im in ims)
    cols = min(6, len(ims))
    rows = math.ceil(len(ims) / cols)
    pad, head = 4, 34
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * pad, head + rows * th + (rows + 1) * pad), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=18)
        small = ImageFont.load_default(size=15)
    except TypeError:
        font = small = ImageFont.load_default()
    d.text((8, 7), f"Motion {_fmt(seg['start'])}-{_fmt(seg['end'])} ({seg['level']}), left to right, top to bottom",
           fill=(255, 200, 0), font=font)
    for k, (im, b) in enumerate(zip(ims, burst)):
        x = pad + (k % cols) * (tw + pad)
        y = head + pad + (k // cols) * (th + pad)
        sheet.paste(im, (x, y))
        label = f"{b['t']:.2f}s"
        bb = d.textbbox((0, 0), label, font=small)
        d.rectangle([x + 3, y + 3, x + 9 + bb[2] - bb[0], y + 8 + bb[3] - bb[1]], fill=(0, 0, 0))
        d.text((x + 6, y + 4), label, fill=(255, 220, 0), font=small)
    sheet.save(out_file, quality=85)
    for b in burst:
        Path(b["file"]).unlink(missing_ok=True)
    return out_file


# --------------------------------------------------------------------------- #
# Audio: whole track
# --------------------------------------------------------------------------- #

def _load_wav(path: Path):
    import numpy as np
    with wave.open(str(path), "rb") as w:
        sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    if sw != 2:
        return None, sr
    x = np.frombuffer(raw, dtype="<i2").astype("float32") / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def _pitch_hz(frame, sr: int, fmin: float = 70.0, fmax: float = 400.0) -> float | None:
    """Very small autocorrelation pitch estimate for one ~40 ms voiced frame."""
    import numpy as np
    frame = frame - frame.mean()
    if np.sqrt((frame ** 2).mean()) < 0.01:
        return None
    ac = np.correlate(frame, frame, mode="full")[len(frame) - 1:]
    lo, hi = int(sr / fmax), min(int(sr / fmin), len(ac) - 1)
    if hi <= lo or ac[0] <= 0:
        return None
    k = lo + int(np.argmax(ac[lo:hi]))
    return sr / k if ac[k] / ac[0] > 0.35 else None


def analyze_audio(wav: Path, offset: float, speech: list[dict], log=print) -> dict:
    """Loudness timeline, silence, bursts, sound-without-speech regions and per-line tone cues.
    `speech` segments get a 'tone' field added in place."""
    try:
        import numpy as np
    except ImportError:
        log("numpy is not installed; skipping sound and tone analysis.")
        return {}
    x, sr = _load_wav(wav)
    if x is None or len(x) < sr // 2:
        return {}
    log("Listening for music, sounds, silence and tone...")
    hop = int(sr * 0.5)                      # 0.5 s windows for the timeline
    n = len(x) // hop
    rms = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) + 1e-9 for i in range(n)])
    db = 20 * np.log10(rms)
    # spectral flatness: low = tonal (music, singing, hum), high = noisy (applause, wind, crowd)
    flat = []
    for i in range(n):
        seg = x[i * hop:(i + 1) * hop]
        spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) + 1e-9
        flat.append(float(np.exp(np.mean(np.log(spec))) / np.mean(spec)))
    flat = np.array(flat)
    times = offset + np.arange(n) * 0.5

    loud_ref = float(np.percentile(db, 90)) if n else -30.0
    silence_db = max(-55.0, loud_ref - 35)
    speaking = np.zeros(n, dtype=bool)
    for sg in speech:
        a = int(max(0, (sg["start"] - offset) / 0.5))
        b = int(min(n, math.ceil((sg["end"] - offset) / 0.5)))
        speaking[a:b] = True

    def runs(mask):
        out, i = [], 0
        while i < len(mask):
            if mask[i]:
                j = i
                while j + 1 < len(mask) and mask[j + 1]:
                    j += 1
                out.append((i, j))
                i = j + 1
            else:
                i += 1
        return out

    events = []
    for a, b in runs(db < silence_db):
        if (b - a + 1) * 0.5 >= 2.0:
            events.append({"start": float(times[a]), "end": float(times[b] + 0.5), "type": "silence"})
    nonspeech = (~speaking) & (db >= silence_db + 6)
    tonal = flat < 0.12
    # split sound-without-speech into tonal (music, singing, hum) and noisy (crowd, applause, effects)
    for mask, kind in ((nonspeech & tonal, "likely music or tonal sound"),
                       (nonspeech & ~tonal, "noise, crowd, applause or effects")):
        for a, b in runs(mask):
            if (b - a + 1) * 0.5 < 1.0:
                continue
            events.append({"start": float(times[a]), "end": float(times[b] + 0.5), "type": kind,
                           "level_db": round(float(np.mean(db[a:b + 1])), 1)})
    med = float(np.median(db)) if n else -30.0
    for i in range(1, n):
        if not speaking[i] and db[i] - db[i - 1] >= 12 and db[i] >= med + 10:
            events.append({"start": float(times[i]), "end": float(times[i] + 0.5), "type": "sudden loud sound",
                           "level_db": round(float(db[i]), 1)})
    events.sort(key=lambda e: e["start"])

    # ---- per-line tone cues ----
    seg_stats = []
    for sg in speech:
        a = int(max(0, (sg["start"] - offset) * sr))
        b = int(min(len(x), (sg["end"] - offset) * sr))
        if b - a < sr // 4:
            seg_stats.append(None)
            continue
        part = x[a:b]
        loud = 20 * math.log10(float(np.sqrt(np.mean(part ** 2))) + 1e-9)
        fl = int(sr * 0.04)
        pitches = [p for p in (_pitch_hz(part[k:k + fl], sr) for k in range(0, len(part) - fl, fl)) if p]
        words = len(sg["text"].split()) or max(1, len(sg["text"]) // 6)
        rate = words / max(0.3, sg["end"] - sg["start"])
        seg_stats.append({"db": loud, "pitch": float(np.median(pitches)) if len(pitches) >= 3 else None,
                          "pitch_var": float(np.std(pitches) / np.mean(pitches)) if len(pitches) >= 3 else None,
                          "rate": rate})
    valid = [s for s in seg_stats if s]
    if valid:
        mdb = float(np.median([s["db"] for s in valid]))
        ps = [s["pitch"] for s in valid if s["pitch"]]
        mp = float(np.median(ps)) if ps else None
        mr = float(np.median([s["rate"] for s in valid]))
        pvs = [s["pitch_var"] for s in valid if s["pitch_var"] is not None]
        mpv = float(np.median(pvs)) if pvs else 0.0
        for sg, st in zip(speech, seg_stats):
            if not st:
                continue
            cues = []
            if st["db"] >= mdb + 6:
                cues.append("loud" if st["db"] < mdb + 12 else "very loud / shouting")
            elif st["db"] <= mdb - 8:
                cues.append("quiet / soft")
            if st["pitch"] and mp:
                if st["pitch"] >= mp * 1.2:
                    cues.append("higher pitch")
                elif st["pitch"] <= mp * 0.82:
                    cues.append("lower pitch")
            if st["pitch_var"] is not None:
                if st["pitch_var"] >= max(0.15, mpv * 1.5):
                    cues.append("animated (pitch moves a lot)")
                elif st["pitch_var"] <= min(0.06, mpv * 0.6 + 0.02):
                    cues.append("flat / monotone")
            if st["rate"] >= mr * 1.4 and st["rate"] >= 2.5:
                cues.append("fast")
            elif st["rate"] <= mr * 0.6:
                cues.append("slow")
            if cues:
                sg["tone"] = cues
    return {"events": events, "loudness_ref_db": round(loud_ref, 1), "silence_db": round(silence_db, 1)}


SOUND_TAG_RE = re.compile(r"[\[(]\s*(music|applause|laugh\w*|cheer\w*|sigh\w*|cough\w*|crying|cries|"
                          r"singing|sings|screams?|gasps?|whistl\w*|bell\w*|beep\w*|noise|"
                          r"silence|inaudible|crowd\w*|clapping|explosion|gunshots?)[^\])]*[\])]|♪+[^♪]*♪*", re.I)


def split_sound_tags(speech: list[dict]) -> list[dict]:
    """Whisper sometimes writes [Music], (laughs), ♪...♪. Move those into sound events."""
    events = []
    for sg in speech:
        tags = [m.group(0) for m in SOUND_TAG_RE.finditer(sg.get("text", ""))]
        for tag in tags:
            label = "music / singing" if "♪" in tag else tag.strip("[]() ").lower()
            events.append({"start": sg["start"], "end": sg["end"], "type": f"heard: {label}"})
        if tags:
            sg["text"] = re.sub(r"\s{2,}", " ", SOUND_TAG_RE.sub("", sg["text"])).strip()
    return events
