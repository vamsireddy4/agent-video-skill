#!/usr/bin/env python3
"""
video_watch.py - turn any video (URL or local file) into something an AI agent can "watch".

It never saves the video. It streams it, pulls out key frames (pictures) and a
timestamped transcript (speech), and writes a timeline package:

    <out>/timeline.md      <- read this first: frames + speech, in time order
    <out>/timeline.json    <- same data, machine-readable
    <out>/transcript.txt   <- speech only, with timestamps
    <out>/frames/*.jpg     <- key frames, named by timestamp
    <out>/sheets/*.jpg     <- contact sheets (several frames per image, labelled)

No AI model is called. The agent that runs this script looks at the frames with
its own vision and reads the transcript, so it works with Claude, Codex, Gemini,
Cursor, Copilot or any agent that can run a command and view images.

Requirements: ffmpeg + ffprobe on PATH. Optional: yt-dlp (web pages / sites),
Pillow (contact sheets), faster-whisper or openai-whisper (speech when no captions).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DIRECT_MEDIA_EXT = (".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".m3u8", ".mpd", ".ts", ".flv", ".ogv")
FFMPEG_NET_OPTS = ["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5"]


def log(msg: str) -> None:
    print(f"[video-watch] {msg}", file=sys.stderr, flush=True)


def fail(msg: str, code: int = 1) -> None:
    log(f"ERROR: {msg}")
    sys.exit(code)


def fmt_ts(sec: float) -> str:
    sec = max(0, int(round(sec)))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_ts(value: str | None) -> float | None:
    """Accept 90, 90.5, 1:30, 01:02:03."""
    if value is None or value == "":
        return None
    parts = str(value).strip().split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        fail(f"Bad time value: {value!r} (use seconds, mm:ss or hh:mm:ss)")
    total = 0.0
    for n in nums:
        total = total * 60 + n
    return total


def run(cmd: list[str], timeout: float | None = None, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=check)


def need(tool: str, hint: str) -> None:
    if not shutil.which(tool):
        fail(f"'{tool}' not found on PATH. {hint}")


# --------------------------------------------------------------------------- #
# 1. Resolve the source into a stream (nothing is downloaded)
# --------------------------------------------------------------------------- #

class Source:
    def __init__(self) -> None:
        self.kind = ""            # local | direct | site
        self.input = ""           # what the user gave us
        self.video_url = ""       # what ffmpeg reads for frames
        self.audio_url = ""       # what ffmpeg reads for audio (may equal video_url)
        self.headers: dict = {}   # HTTP headers some sites require
        self.title = ""
        self.duration: float | None = None
        self.uploader = ""
        self.description = ""
        self.webpage_url = ""
        self.chapters: list = []
        self.info: dict = {}      # raw yt-dlp info (for captions)

    def ffmpeg_input(self, url: str) -> list[str]:
        args: list[str] = []
        if url.startswith(("http://", "https://")):
            args += FFMPEG_NET_OPTS
            if self.headers:
                ua = self.headers.get("User-Agent")
                if ua:
                    args += ["-user_agent", ua]
                rest = "".join(f"{k}: {v}\r\n" for k, v in self.headers.items() if k.lower() != "user-agent")
                if rest:
                    args += ["-headers", rest]
        return args + ["-i", url]


def ytdlp_base(args) -> list[str]:
    cmd = ["yt-dlp", "--no-warnings", "--no-playlist"]
    if args.cookies_from_browser:
        cmd += ["--cookies-from-browser", args.cookies_from_browser]
    if args.cookies:
        cmd += ["--cookies", args.cookies]
    return cmd


def resolve_source(src: str, args) -> Source:
    s = Source()
    s.input = src

    p = Path(src).expanduser()
    if p.exists():
        s.kind = "local"
        s.video_url = s.audio_url = str(p.resolve())
        s.title = p.stem
        return s

    if not src.startswith(("http://", "https://")):
        fail(f"'{src}' is neither an existing file nor an http(s) URL.")

    path_part = src.split("?", 1)[0].lower()
    if path_part.endswith(DIRECT_MEDIA_EXT) or args.direct:
        s.kind = "direct"
        s.video_url = s.audio_url = src
        s.title = Path(path_part).stem or "video"
        return s

    # A web page: ask yt-dlp where the real stream is (no download).
    need("yt-dlp", "Install it with: pip install -U yt-dlp")
    s.kind = "site"
    fmt = (f"bv*[height<={args.max_height}]+ba/b[height<={args.max_height}]/bv*+ba/b")
    cmd = ytdlp_base(args) + ["-J", "-f", fmt, src]
    log("Finding the video stream (no download)...")
    try:
        r = run(cmd, timeout=180)
    except subprocess.TimeoutExpired:
        fail("yt-dlp timed out while reading the page.")
    if r.returncode != 0 or not r.stdout.strip():
        err = (r.stderr or "").strip().splitlines()
        err_txt = err[-1] if err else "unknown error"
        if re.search(r"DRM", r.stderr or "", re.I):
            fail("This video is DRM-protected. It cannot be watched (and the tool will not try to bypass DRM).")
        fail("yt-dlp could not find a video on this page: " + err_txt +
             "\nTips: update yt-dlp (pip install -U yt-dlp); for login-only videos pass "
             "--cookies-from-browser chrome; for unsupported sites use a browser-screenshot fallback.")
    info = json.loads(r.stdout)
    if info.get("_type") == "playlist" and info.get("entries"):
        info = next((e for e in info["entries"] if e), info)
    s.info = info
    s.title = info.get("title") or "video"
    s.duration = info.get("duration")
    s.uploader = info.get("uploader") or info.get("channel") or ""
    s.description = (info.get("description") or "")[:1500]
    s.webpage_url = info.get("webpage_url") or src
    s.chapters = info.get("chapters") or []
    if info.get("is_live"):
        log("Note: this is a live stream; only what plays from now on can be sampled.")

    req = info.get("requested_formats")
    if req:
        for f in req:
            if f.get("vcodec") not in (None, "none") and not s.video_url:
                s.video_url = f["url"]
                s.headers = f.get("http_headers") or info.get("http_headers") or {}
            if f.get("acodec") not in (None, "none") and not s.audio_url:
                s.audio_url = f["url"]
    if not s.video_url:
        s.video_url = info.get("url") or ""
        s.headers = info.get("http_headers") or {}
    if not s.audio_url:
        s.audio_url = s.video_url
    if not s.video_url:
        fail("yt-dlp found the page but no playable stream URL (it may be DRM-protected or need a login).")
    return s


def probe_duration(s: Source) -> float | None:
    if s.duration:
        return float(s.duration)
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json"]
    cmd += s.ffmpeg_input(s.video_url)[:-2] + [s.video_url]
    try:
        r = run(cmd, timeout=90)
        d = json.loads(r.stdout or "{}").get("format", {}).get("duration")
        return float(d) if d not in (None, "N/A") else None
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# 2. Key frames
# --------------------------------------------------------------------------- #

def grab_frame(s: Source, t: float, out_file: Path, width: int) -> bool:
    """Seek inside the stream and grab one frame. Over HTTP this uses range
    requests, so only a small piece of the video is fetched."""
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}"]
    cmd += s.ffmpeg_input(s.video_url)
    cmd += ["-frames:v", "1", "-vf", f"scale='min({width},iw)':-2", "-q:v", "3", str(out_file)]
    try:
        r = run(cmd, timeout=120)
    except subprocess.TimeoutExpired:
        return False
    return r.returncode == 0 and out_file.exists() and out_file.stat().st_size > 0


def gap_fill_times(have: list[float], start: float, end: float, n: int) -> list[float]:
    """Pick n new timestamps, each in the middle of the biggest remaining gap."""
    pts = sorted(set([start] + have + [end]))
    new: list[float] = []
    for _ in range(n):
        gaps = [(pts[i + 1] - pts[i], i) for i in range(len(pts) - 1)]
        if not gaps:
            break
        size, i = max(gaps)
        if size < 1.0:
            break
        mid = pts[i] + size / 2
        new.append(mid)
        pts.insert(i + 1, mid)
    return sorted(new)


def frame_name(idx: int, t: float) -> str:
    t_int = int(round(t))
    return f"frame_{idx:04d}_{t_int // 3600:02d}h{(t_int % 3600) // 60:02d}m{t_int % 60:02d}s.jpg"


def interval_times(start: float, end: float, interval: float, max_frames: int) -> list[float]:
    span = max(0.0, end - start)
    if span <= 0:
        return [start]
    n = int(span // interval) + 1
    if n > max_frames:
        # spread max_frames evenly across the span instead
        step = span / max_frames
        return [start + step * (i + 0.5) for i in range(max_frames)]
    first = start + min(interval / 2, span / 2) if start == 0 and interval > 2 else start
    return [t for t in (first + i * interval for i in range(n)) if t < end] or [start]


def frames_by_interval(s: Source, times: list[float], frames_dir: Path, width: int, workers: int,
                       prefix: str = "grab_") -> list[dict]:
    log(f"Grabbing {len(times)} frames by seeking inside the stream...")
    jobs = {}
    results: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for i, t in enumerate(times, 1):
            f = frames_dir / f"{prefix}{i:05d}.jpg"
            jobs[ex.submit(grab_frame, s, t, f, width)] = (t, f)
        for fut in cf.as_completed(jobs):
            t, f = jobs[fut]
            if fut.result():
                results.append({"t": round(t, 2), "file": f})
    results.sort(key=lambda x: x["t"])
    return results


def frames_by_scene(s: Source, start: float, end: float | None, threshold: float,
                    frames_dir: Path, width: int, timeout: float) -> list[dict]:
    """One pass through the stream; keep a frame only when the picture changes.
    The stream is read but never written to disk."""
    tmp_pattern = frames_dir / "scene_%05d.jpg"
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-y"]
    if start:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += s.ffmpeg_input(s.video_url)
    if end is not None:
        cmd += ["-t", f"{max(0.1, end - start):.3f}"]
    vf = f"select='eq(n\\,0)+gt(scene\\,{threshold})',showinfo,scale='min({width},iw)':-2"
    cmd += ["-an", "-sn", "-vf", vf, "-fps_mode", "vfr", "-q:v", "3", str(tmp_pattern)]
    log(f"Scanning the stream for scene changes (threshold {threshold})...")
    try:
        r = run(cmd, timeout=timeout)
        stderr = r.stderr
    except subprocess.TimeoutExpired as e:
        log("Scene scan hit the time limit; using the frames found so far.")
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
    times = [float(m.group(1)) for m in re.finditer(r"pts_time:\s*([0-9.]+)", stderr)]
    files = sorted(frames_dir.glob("scene_*.jpg"))
    results = []
    for i, f in enumerate(files):
        t = (times[i] if i < len(times) else 0.0) + start
        results.append({"t": round(t, 2), "file": f})
    return results


def thin_evenly(frames: list[dict], k: int) -> list[dict]:
    if len(frames) <= k:
        return frames
    keep_idx = {round(i * (len(frames) - 1) / (k - 1)) for i in range(k)} if k > 1 else {0}
    kept, dropped = [], []
    for i, fr in enumerate(frames):
        (kept if i in keep_idx else dropped).append(fr)
    for fr in dropped:
        try:
            fr["file"].unlink()
        except OSError:
            pass
    return kept


def drop_near_duplicates(frames: list[dict], max_diff: float = 2.5) -> list[dict]:
    """Remove frames that look almost identical to the previous kept one (needs Pillow)."""
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:
        return frames
    kept, prev = [], None
    for fr in frames:
        try:
            img = Image.open(fr["file"]).convert("RGB").resize((64, 36))
        except Exception:
            kept.append(fr)
            continue
        if prev is not None:
            diff = sum(ImageStat.Stat(ImageChops.difference(img, prev)).mean) / 3
            if diff < max_diff:
                fr["file"].unlink(missing_ok=True)
                continue
        kept.append(fr)
        prev = img
    return kept


def renumber(frames: list[dict], frames_dir: Path) -> list[dict]:
    tmp = []
    for i, fr in enumerate(frames, 1):
        t = fr["t"]
        dst = frames_dir / ("._" + frame_name(i, t))
        fr["file"].rename(dst)
        tmp.append({"t": t, "file": dst})
    for fr in tmp:
        final = frames_dir / fr["file"].name[2:]
        fr["file"].rename(final)
        fr["file"] = final
    return tmp


# --------------------------------------------------------------------------- #
# 3. Speech: captions first, then embedded subtitles, then Whisper
# --------------------------------------------------------------------------- #

TAG_RE = re.compile(r"<[^>]+>")
VTT_TIME = re.compile(r"(\d+:)?(\d{1,2}):(\d{2})[.,](\d{3})\s*-->\s*(\d+:)?(\d{1,2}):(\d{2})[.,](\d{3})")


def _vtt_secs(h, m, s, ms) -> float:
    return (int(h[:-1]) if h else 0) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_vtt(text: str) -> list[dict]:
    """Parse WebVTT/SRT and collapse YouTube-style rolling auto-captions."""
    segs: list[dict] = []
    cur = None
    lines = text.replace("\r", "").split("\n")
    for idx, line in enumerate(lines):
        m = VTT_TIME.search(line)
        if m:
            if cur and cur["lines"]:
                segs.append(cur)
            g = m.groups()
            cur = {"start": _vtt_secs(g[0], g[1], g[2], g[3]), "end": _vtt_secs(g[4], g[5], g[6], g[7]), "lines": []}
            continue
        if cur is None:
            continue  # header (WEBVTT, Kind:, Language:, STYLE...)
        clean = html.unescape(TAG_RE.sub("", line)).replace("\xa0", " ").strip()
        if not clean:
            continue
        nxt = lines[idx + 1] if idx + 1 < len(lines) else ""
        if clean.isdigit() and VTT_TIME.search(nxt):
            continue  # SRT cue number
        cur["lines"].append(clean)
    if cur and cur["lines"]:
        segs.append(cur)
    out: list[dict] = []
    seen_last = ""
    for sg in segs:
        new_lines = [l for l in sg["lines"] if l != seen_last]
        if out:
            prev_lines = out[-1]["_lines"]
            new_lines = [l for l in new_lines if l not in prev_lines]
        if not new_lines:
            continue
        txt = " ".join(new_lines).strip()
        if out and out[-1]["text"] == txt:
            out[-1]["end"] = sg["end"]
            continue
        out.append({"start": round(sg["start"], 2), "end": round(sg["end"], 2), "text": txt, "_lines": sg["lines"]})
        seen_last = sg["lines"][-1]
    for o in out:
        o.pop("_lines", None)
    return out


def pick_caption_lang(available: dict, wanted: str | None) -> str | None:
    if not available:
        return None
    keys = [k for k in available if k != "live_chat"]
    if not keys:
        return None
    if wanted:
        for k in keys:
            if k == wanted or k.startswith(wanted + "-"):
                return k
    for k in keys:
        if k.endswith("-orig"):
            return k
    for k in keys:
        if k == "en" or k.startswith("en-"):
            return k
    return keys[0]


def captions_from_site(s: Source, args, work: Path) -> tuple[list[dict], str]:
    if s.kind != "site" or not s.info:
        return [], ""
    manual = s.info.get("subtitles") or {}
    auto = s.info.get("automatic_captions") or {}
    lang = pick_caption_lang(manual, args.lang)
    use_auto = False
    if not lang:
        lang = pick_caption_lang(auto, args.lang)
        use_auto = bool(lang)
    if not lang:
        return [], ""
    log(f"Fetching {'auto-generated' if use_auto else 'uploaded'} captions ({lang}), no video download...")
    sub_dir = work / "_subs"
    sub_dir.mkdir(exist_ok=True)
    cmd = ytdlp_base(args) + ["--skip-download", "--sub-langs", lang, "--sub-format", "vtt/srt/best",
                              "--convert-subs", "vtt", "-o", str(sub_dir / "subs.%(ext)s"),
                              "--write-auto-subs" if use_auto else "--write-subs", s.webpage_url or s.input]
    try:
        run(cmd, timeout=180)
    except subprocess.TimeoutExpired:
        return [], ""
    files = sorted(sub_dir.glob("subs*.vtt")) + sorted(sub_dir.glob("subs*.srt"))
    segs = parse_vtt(files[0].read_text(encoding="utf-8", errors="ignore")) if files else []
    shutil.rmtree(sub_dir, ignore_errors=True)
    return segs, (f"auto-captions ({lang})" if use_auto else f"captions ({lang})") if segs else ""


def captions_embedded(s: Source, start: float, end: float | None) -> tuple[list[dict], str]:
    """Subtitle track inside the file/stream itself (common in .mkv/.mp4)."""
    cmd = ["ffprobe", "-v", "error", "-select_streams", "s", "-show_entries", "stream=index", "-of", "csv=p=0"]
    cmd += s.ffmpeg_input(s.video_url)[:-2] + [s.video_url]
    try:
        r = run(cmd, timeout=60)
    except subprocess.TimeoutExpired:
        return [], ""
    if not r.stdout.strip():
        return [], ""
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error"] + s.ffmpeg_input(s.video_url)
    cmd += ["-map", "0:s:0", "-f", "webvtt", "-"]
    try:
        r = run(cmd, timeout=300)
    except subprocess.TimeoutExpired:
        return [], ""
    segs = parse_vtt(r.stdout or "")
    segs = [x for x in segs if x["end"] >= start and (end is None or x["start"] <= end)]
    return segs, "embedded subtitles" if segs else ""


def whisper_transcribe(s: Source, args, work: Path, start: float, end: float | None) -> tuple[list[dict], str]:
    engine = None
    try:
        import faster_whisper  # noqa: F401
        engine = "faster-whisper"
    except ImportError:
        try:
            import whisper  # noqa: F401
            engine = "openai-whisper"
        except ImportError:
            pass
    if not engine:
        log("No captions found and no Whisper installed - continuing without speech. "
            "(pip install faster-whisper to enable it)")
        return [], ""

    wav = work / "_audio.wav"
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
    if start:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += s.ffmpeg_input(s.audio_url)
    if end is not None:
        cmd += ["-t", f"{max(0.1, end - start):.3f}"]
    cmd += ["-vn", "-ac", "1", "-ar", "16000", "-f", "wav", str(wav)]
    log("Streaming the audio track for transcription...")
    try:
        r = run(cmd, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        log("Audio streaming timed out; continuing without speech.")
        wav.unlink(missing_ok=True)
        return [], ""
    if r.returncode != 0 or not wav.exists() or wav.stat().st_size < 2000:
        log("This video has no usable audio track.")
        wav.unlink(missing_ok=True)
        return [], ""

    segs: list[dict] = []
    log(f"Transcribing with {engine} ({args.whisper_model} model)...")
    try:
        if engine == "faster-whisper":
            from faster_whisper import WhisperModel
            model = WhisperModel(args.whisper_model, device="auto", compute_type="int8")
            it, _ = model.transcribe(str(wav), language=args.lang, vad_filter=True)
            for sg in it:
                segs.append({"start": round(sg.start + start, 2), "end": round(sg.end + start, 2), "text": sg.text.strip()})
        else:
            import whisper
            model = whisper.load_model(args.whisper_model)
            res = model.transcribe(str(wav), language=args.lang, fp16=False)
            for sg in res.get("segments", []):
                segs.append({"start": round(sg["start"] + start, 2), "end": round(sg["end"] + start, 2), "text": sg["text"].strip()})
    except Exception as e:  # model download blocked, no space, etc.
        log(f"Whisper failed ({type(e).__name__}: {e}); continuing without speech.")
        segs = []
    finally:
        wav.unlink(missing_ok=True)
    segs = [x for x in segs if x["text"]]
    return segs, f"whisper ({args.whisper_model})" if segs else ""


def get_transcript(s: Source, args, work: Path, start: float, end: float | None) -> tuple[list[dict], str]:
    mode = args.transcript
    if mode == "none":
        return [], "none"
    segs, how = [], ""
    if mode in ("auto", "captions"):
        segs, how = captions_from_site(s, args, work)
        if not segs:
            segs, how = captions_embedded(s, start, end)
    if not segs and mode in ("auto", "whisper"):
        segs, how = whisper_transcribe(s, args, work, start, end)
    if segs:
        segs = [x for x in segs if x["end"] >= start and (end is None or x["start"] <= end)]
    return segs, how or "none found"


# --------------------------------------------------------------------------- #
# 4. Contact sheets (many frames in one image, for agents with image limits)
# --------------------------------------------------------------------------- #

def make_sheets(frames: list[dict], sheets_dir: Path, per_sheet: int, cols: int) -> list[Path]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        log("Pillow not installed - skipping contact sheets (pip install pillow).")
        return []
    if not frames:
        return []
    sheets_dir.mkdir(parents=True, exist_ok=True)
    tile_w = 480
    try:
        font = ImageFont.load_default(size=22)
    except TypeError:
        font = ImageFont.load_default()
    out = []
    for si in range(0, len(frames), per_sheet):
        chunk = frames[si:si + per_sheet]
        tiles = []
        for fr in chunk:
            im = Image.open(fr["file"]).convert("RGB")
            h = max(1, int(im.height * tile_w / im.width))
            tiles.append((im.resize((tile_w, h)), fr["t"]))
        tile_h = max(t[0].height for t in tiles)
        c = min(cols, len(tiles))
        rows = math.ceil(len(tiles) / c)
        pad = 6
        sheet = Image.new("RGB", (c * tile_w + (c + 1) * pad, rows * tile_h + (rows + 1) * pad), (24, 24, 24))
        d = ImageDraw.Draw(sheet)
        for i, (im, t) in enumerate(tiles):
            x = pad + (i % c) * (tile_w + pad)
            y = pad + (i // c) * (tile_h + pad)
            sheet.paste(im, (x, y))
            label = f" {fmt_ts(t)} "
            bbox = d.textbbox((0, 0), label, font=font)
            d.rectangle([x + 6, y + 6, x + 12 + bbox[2] - bbox[0], y + 12 + bbox[3] - bbox[1]], fill=(0, 0, 0))
            d.text((x + 9, y + 7), label, fill=(255, 220, 0), font=font)
        p = sheets_dir / f"sheet_{si // per_sheet + 1:02d}_{fmt_ts(chunk[0]['t']).replace(':', 'm')}-{fmt_ts(chunk[-1]['t']).replace(':', 'm')}.jpg"
        sheet.save(p, quality=85)
        out.append(p)
    return out


# --------------------------------------------------------------------------- #
# 5. Timeline package
# --------------------------------------------------------------------------- #

def build_timeline(frames: list[dict], segs: list[dict], start: float, end: float) -> list[dict]:
    """Attach each speech segment to the frame that was on screen when it started."""
    items = []
    for i, fr in enumerate(frames):
        lo = start if i == 0 else fr["t"]
        hi = frames[i + 1]["t"] if i + 1 < len(frames) else end + 1
        speech = [sg for sg in segs if lo <= sg["start"] < hi]
        items.append({"t": fr["t"], "until": round(hi if i + 1 < len(frames) else end, 2),
                      "frame": fr["file"], "speech": speech})
    if not frames and segs:
        items.append({"t": start, "until": end, "frame": None, "speech": segs})
    return items


def write_outputs(out: Path, s: Source, frames, segs, how, sheets, start, end, args) -> dict:
    timeline = build_timeline(frames, segs, start, end)
    rel = lambda p: str(Path(p).relative_to(out)) if p else None  # noqa: E731

    md = [f"# Video timeline: {s.title}", ""]
    md.append(f"- Source: {s.webpage_url or s.input}")
    if s.uploader:
        md.append(f"- Channel / uploader: {s.uploader}")
    md.append(f"- Duration: {fmt_ts(s.duration) if s.duration else 'unknown'}"
              + (f" (covered {fmt_ts(start)}–{fmt_ts(end)})" if args.start or args.end else ""))
    md.append(f"- Frames: {len(frames)} ({args.mode_used}); contact sheets: {len(sheets)}")
    md.append(f"- Speech: {how} ({len(segs)} segments)")
    md.append("")
    md.append("How to read this: each block is one key frame (open the image file to see it) followed by "
              "what was said while that frame was on screen. Frames are snapshots, not continuous video, "
              "so fast actions between two frames can be missed.")
    if s.chapters:
        md += ["", "## Chapters", ""]
        md += [f"- {fmt_ts(c.get('start_time', 0))} {c.get('title', '')}" for c in s.chapters]
    if s.description:
        md += ["", "## Description (from the page)", "", s.description.strip()]
    md += ["", "## Timeline", ""]
    for it in timeline:
        head = f"### [{fmt_ts(it['t'])}]"
        md.append(head + (f" frame: `{rel(it['frame'])}`" if it["frame"] else " (no frames)"))
        if it["speech"]:
            for sg in it["speech"]:
                md.append(f"- {fmt_ts(sg['start'])} – {sg['text']}")
        else:
            md.append("- (no speech)")
        md.append("")
    if sheets:
        md += ["## Contact sheets", "", "Each sheet shows several frames with their timestamps in the corner:", ""]
        md += [f"- `{rel(p)}`" for p in sheets]
    (out / "timeline.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    (out / "transcript.txt").write_text(
        "\n".join(f"[{fmt_ts(sg['start'])}] {sg['text']}" for sg in segs) + ("\n" if segs else ""), encoding="utf-8")

    data = {
        "title": s.title, "source": s.webpage_url or s.input, "source_kind": s.kind,
        "duration_seconds": s.duration, "covered": [start, end], "uploader": s.uploader,
        "frame_mode": args.mode_used, "speech_source": how,
        "chapters": s.chapters, "description": s.description,
        "frames": [{"t": f["t"], "time": fmt_ts(f["t"]), "file": rel(f["file"])} for f in frames],
        "contact_sheets": [rel(p) for p in sheets],
        "transcript": segs,
        "timeline": [{"t": it["t"], "time": fmt_ts(it["t"]), "until": it["until"],
                      "frame": rel(it["frame"]), "speech": it["speech"]} for it in timeline],
    }
    (out / "timeline.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Stream a video (any URL or local file) into key frames + timestamped speech for an AI agent.")
    ap.add_argument("source", help="Video page URL, direct .mp4/.m3u8 URL, or local file path")
    ap.add_argument("-o", "--out", default=None, help="Output folder (default: ./video-watch-<title>)")
    ap.add_argument("--mode", choices=["auto", "scene", "interval"], default="auto",
                    help="scene = keep frames where the picture changes; interval = one frame every N seconds; "
                         "auto = scene for videos up to 20 min, interval for longer")
    ap.add_argument("--interval", type=float, default=None, help="Seconds between frames in interval mode")
    ap.add_argument("--scene-threshold", type=float, default=0.3, help="0-1, lower = more frames (default 0.3)")
    ap.add_argument("--max-frames", type=int, default=40, help="Upper limit on frames (default 40)")
    ap.add_argument("--min-frames", type=int, default=8, help="Top up with evenly spaced frames if scene mode finds fewer")
    ap.add_argument("--width", type=int, default=1000, help="Max frame width in px (default 1000)")
    ap.add_argument("--start", default=None, help="Start time (sec, mm:ss or hh:mm:ss)")
    ap.add_argument("--end", default=None, help="End time")
    ap.add_argument("--transcript", choices=["auto", "captions", "whisper", "none"], default="auto")
    ap.add_argument("--lang", default=None, help="Language code for captions/Whisper, e.g. en, te, hi")
    ap.add_argument("--whisper-model", default="base", help="Whisper model size: tiny, base, small, medium...")
    ap.add_argument("--no-sheets", action="store_true", help="Do not build contact sheets")
    ap.add_argument("--sheet-size", type=int, default=6, help="Frames per contact sheet (default 6)")
    ap.add_argument("--max-height", type=int, default=720, help="Highest stream resolution to request (default 720)")
    ap.add_argument("--cookies-from-browser", default=None, help="e.g. chrome, firefox - for videos that need YOUR login")
    ap.add_argument("--cookies", default=None, help="Path to a cookies.txt file")
    ap.add_argument("--direct", action="store_true", help="Treat the URL as a direct media stream (skip yt-dlp)")
    ap.add_argument("--workers", type=int, default=4, help="Parallel frame grabs in interval mode")
    ap.add_argument("--timeout", type=float, default=1800, help="Max seconds for a full-stream pass (scene scan / audio)")
    args = ap.parse_args()

    need("ffmpeg", "Install ffmpeg: https://ffmpeg.org/download.html (brew install ffmpeg / winget install ffmpeg / apt install ffmpeg)")
    need("ffprobe", "ffprobe ships with ffmpeg.")

    s = resolve_source(args.source, args)
    s.duration = probe_duration(s)

    start = parse_ts(args.start) or 0.0
    end = parse_ts(args.end)
    if s.duration and (end is None or end > s.duration):
        end = s.duration
    if end is not None and end <= start:
        fail("--end must be after --start")

    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", s.title).strip("-")[:60] or "video"
    out = Path(args.out or f"video-watch-{slug}").expanduser().resolve()
    frames_dir = out / "frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    if (out / "sheets").exists():
        shutil.rmtree(out / "sheets")
    frames_dir.mkdir(parents=True, exist_ok=True)

    span = (end - start) if end is not None else None
    mode = args.mode
    if mode == "auto":
        mode = "scene" if (span is not None and span <= 20 * 60) else "interval"
    if mode == "interval" and span is None:
        log("Duration unknown (live or unprobeable stream); using scene mode with a time limit.")
        mode = "scene"
    args.mode_used = mode

    if mode == "interval":
        interval = args.interval or max(2.0, span / args.max_frames)
        frames = frames_by_interval(s, interval_times(start, end, interval, args.max_frames),
                                    frames_dir, args.width, args.workers)
        frames = drop_near_duplicates(frames)
        args.mode_used = f"interval, every ~{interval:.0f}s"
    else:
        frames = frames_by_scene(s, start, end, args.scene_threshold, frames_dir, args.width, args.timeout)
        frames = drop_near_duplicates(frames)
        if span is not None and len(frames) < args.min_frames:
            # Scene detection can miss changes (e.g. two slides of similar brightness).
            # Fill the biggest gaps, then drop any that turn out identical to their neighbour.
            extra_t = gap_fill_times([f["t"] for f in frames], start, end, args.min_frames - len(frames))
            if extra_t:
                log(f"Scene scan found {len(frames)} frames; checking {len(extra_t)} more in the biggest gaps.")
                frames += frames_by_interval(s, extra_t, frames_dir, args.width, args.workers, prefix="gap_")
                frames.sort(key=lambda f: f["t"])
                frames = drop_near_duplicates(frames)
        frames = thin_evenly(frames, args.max_frames)
        args.mode_used = f"scene changes (threshold {args.scene_threshold})"
    frames = renumber(frames, frames_dir)
    if not frames:
        log("No frames could be extracted (audio-only stream, DRM, or the server refused range requests).")

    effective_end = end if end is not None else (frames[-1]["t"] if frames else start)
    segs, how = get_transcript(s, args, out, start, end)

    sheets = [] if args.no_sheets else make_sheets(frames, out / "sheets", args.sheet_size, cols=3 if args.sheet_size > 4 else 2)
    data = write_outputs(out, s, frames, segs, how, sheets, start, effective_end, args)

    summary = {
        "ok": bool(frames or segs),
        "out_dir": str(out),
        "read_first": str(out / "timeline.md"),
        "title": data["title"],
        "duration": fmt_ts(s.duration) if s.duration else None,
        "frames": len(frames),
        "contact_sheets": len(sheets),
        "speech_source": how,
        "speech_segments": len(segs),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
