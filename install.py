#!/usr/bin/env python3
"""
video-watch installer: one command sets up everything.

  macOS / Linux:
    curl -fsSL https://raw.githubusercontent.com/vamsireddy4/claude-watch/main/install.py | python3 -
  Windows (PowerShell):
    irm https://raw.githubusercontent.com/vamsireddy4/claude-watch/main/install.py | python -
  From a clone:
    python3 install.py

What it does (no admin rights needed):
  1. Creates a private Python environment in ~/.video-watch/venv
  2. Installs yt-dlp, Pillow, faster-whisper and a bundled ffmpeg (imageio-ffmpeg) into it
  3. Downloads the Whisper speech models (base + small) so the first video is fast
  4. Finds the AI agents on this computer (Claude Code, Codex, Gemini CLI, Cursor) and installs
     the skill into each one's skills folder (or updates it if it is already there)
  5. Runs a self-check and prints where everything went

Options:
  --agents claude,codex,gemini,cursor,agents   choose agents instead of auto-detecting
  --deps-only        only set up the environment (used by the skill on first use)
  --no-models        skip downloading the Whisper models now (they download on first use)
  --uninstall        remove the skill folders this installer created and ~/.video-watch
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = os.environ.get("VIDEO_WATCH_REPO", "https://github.com/vamsireddy4/claude-watch")
BRANCH = "main"
SKILL = "video-watch"
PACKAGES = ["yt-dlp", "pillow", "numpy", "faster-whisper", "imageio-ffmpeg"]
MODELS = ["base", "small"]

HOME = Path.home()
VW_HOME = Path(os.environ.get("VIDEO_WATCH_HOME", HOME / ".video-watch"))
VENV = VW_HOME / "venv"
VENV_PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

# agent -> (folder that shows the agent is installed, skills folder to install into)
AGENTS = {
    "claude": ("Claude Code", HOME / ".claude", HOME / ".claude" / "skills"),
    "codex": ("Codex", HOME / ".codex", HOME / ".agents" / "skills"),
    "gemini": ("Gemini CLI", HOME / ".gemini", HOME / ".gemini" / "skills"),
    "cursor": ("Cursor", HOME / ".cursor", HOME / ".cursor" / "skills"),
    "agents": ("Shared agents folder (Codex, Copilot, others)", None, HOME / ".agents" / "skills"),
}


def say(msg: str = "") -> None:
    print(msg, flush=True)


def step(msg: str) -> None:
    say(f"\n==> {msg}")


def run(cmd: list[str], quiet: bool = False, check: bool = True) -> int:
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL if quiet else None,
                       stderr=subprocess.STDOUT if quiet else None)
    if check and r.returncode != 0:
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(cmd)}")
    return r.returncode


def local_repo() -> Path | None:
    """The folder this installer lives in, if it is a copy of the skill."""
    try:
        here = Path(__file__).resolve().parent
    except NameError:
        return None
    if (here / "SKILL.md").exists() and (here / "scripts" / "video_watch.py").exists():
        return here
    return None


# --------------------------------------------------------------------------- #
# dependencies
# --------------------------------------------------------------------------- #

def setup_env(with_models: bool) -> bool:
    if sys.version_info < (3, 9):
        say(f"Python 3.9 or newer is needed (this is {sys.version.split()[0]}). "
            "Get it from https://www.python.org/downloads/")
        return False

    step(f"Creating the private Python environment in {VENV}")
    if not VENV_PY.exists():
        VW_HOME.mkdir(parents=True, exist_ok=True)
        try:
            run([sys.executable, "-m", "venv", str(VENV)])
        except Exception as e:
            say(f"Could not create it ({e}). On Ubuntu/Debian install the venv module first: "
                "sudo apt install python3-venv")
            return False
    else:
        say("already there, updating it")

    step("Installing yt-dlp, Pillow, faster-whisper and a bundled ffmpeg (a few minutes the first time)")
    run([str(VENV_PY), "-m", "pip", "install", "-q", "-U", "pip"], check=False)
    ok = True
    for pkg in PACKAGES:
        rc = run([str(VENV_PY), "-m", "pip", "install", "-q", "-U", pkg], check=False)
        say(f"  {'ok  ' if rc == 0 else 'FAIL'} {pkg}")
        if rc != 0 and pkg != "faster-whisper":
            ok = False
    if run([str(VENV_PY), "-c", "import faster_whisper"], quiet=True, check=False) != 0:
        say("  note: faster-whisper did not install, so videos without captions will have no speech")

    ff = shutil.which("ffmpeg")
    say(f"  ffmpeg: {'using the system ffmpeg at ' + ff if ff else 'using the bundled ffmpeg (imageio-ffmpeg)'}")
    if not (shutil.which("deno") or shutil.which("node") or shutil.which("bun")):
        say("  tip: recent yt-dlp versions may need a JavaScript runtime for YouTube. If YouTube links fail,")
        say("       install Deno (https://deno.com) or Node.js and run this installer again.")

    if with_models and run([str(VENV_PY), "-c", "import faster_whisper"], quiet=True, check=False) == 0:
        step(f"Downloading Whisper speech models: {', '.join(MODELS)} (about 650 MB, one time)")
        for m in MODELS:
            code = f"from faster_whisper import WhisperModel; WhisperModel({m!r}, device='cpu', compute_type='int8')"
            rc = run([str(VENV_PY), "-c", code], quiet=True, check=False)
            say(f"  {'ok  ' if rc == 0 else 'skip'} {m}" + ("" if rc == 0 else " (will download on first use)"))
    return ok


# --------------------------------------------------------------------------- #
# skill folders
# --------------------------------------------------------------------------- #

def pick_agents(arg: str | None) -> list[str]:
    if arg:
        names = [a.strip().lower() for a in arg.split(",") if a.strip()]
        bad = [a for a in names if a not in AGENTS]
        if bad:
            raise SystemExit(f"Unknown agent(s): {', '.join(bad)}. Choose from: {', '.join(AGENTS)}")
        return names
    found = [k for k, (_, marker, _) in AGENTS.items() if marker is not None and marker.exists()]
    return found or ["agents"]


def download_zip(target: Path) -> None:
    url = f"{REPO}/archive/refs/heads/{BRANCH}.zip"
    with urllib.request.urlopen(url, timeout=120) as r:
        data = r.read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root = z.namelist()[0].split("/")[0]
        tmp = target.parent / f".{SKILL}-download"
        shutil.rmtree(tmp, ignore_errors=True)
        z.extractall(tmp)
        (tmp / root).rename(target)
        shutil.rmtree(tmp, ignore_errors=True)


def install_into(skills_dir: Path, src: Path | None) -> str:
    target = skills_dir / SKILL
    skills_dir.mkdir(parents=True, exist_ok=True)
    if src and target.resolve() == src.resolve():
        return "already here (this copy)"
    if target.exists():
        if (target / ".git").exists() and shutil.which("git"):
            rc = run(["git", "-C", str(target), "pull", "-q", "--ff-only"], quiet=True, check=False)
            return "updated" if rc == 0 else "kept (could not update; it has local changes)"
        return "kept (folder already exists)"
    if shutil.which("git"):
        rc = run(["git", "clone", "-q", "--depth", "1", "-b", BRANCH, REPO, str(target)], quiet=True, check=False)
        if rc == 0:
            return "installed"
    if src:
        shutil.copytree(src, target, ignore=shutil.ignore_patterns(".git", "__pycache__", "video-watch-*"))
        return "installed (copied)"
    download_zip(target)
    return "installed (downloaded)"


def uninstall() -> None:
    step("Removing video-watch")
    for key, (label, _, skills_dir) in AGENTS.items():
        target = skills_dir / SKILL
        if (target / "SKILL.md").exists() and "name: video-watch" in (target / "SKILL.md").read_text(errors="ignore"):
            shutil.rmtree(target)
            say(f"  removed {target}")
    if VW_HOME.exists():
        shutil.rmtree(VW_HOME)
        say(f"  removed {VW_HOME}")
    say("Done. Whisper models stay in the Hugging Face cache (~/.cache/huggingface) if you want them for other tools.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Install the video-watch agent skill and everything it needs.")
    ap.add_argument("--agents", help="comma list: " + ",".join(AGENTS) + " (default: detect)")
    ap.add_argument("--deps-only", action="store_true", help="only set up the Python environment and tools")
    ap.add_argument("--no-models", action="store_true", help="do not pre-download Whisper models")
    ap.add_argument("--uninstall", action="store_true", help="remove the installed skill folders and ~/.video-watch")
    args = ap.parse_args()

    if args.uninstall:
        uninstall()
        return

    say("video-watch installer")
    src = local_repo()
    env_ok = setup_env(with_models=not args.no_models)

    results = []
    if not args.deps_only:
        step("Installing the skill for your AI agents")
        for key in pick_agents(args.agents):
            label, _, skills_dir = AGENTS[key]
            try:
                status = install_into(skills_dir, src)
            except Exception as e:
                status = f"FAILED ({e})"
            results.append((label, skills_dir / SKILL, status))
            say(f"  {label:<14} {skills_dir / SKILL}  ->  {status}")

    step("Self-check")
    script = None
    for _, path, _ in results:
        if (path / "scripts" / "video_watch.py").exists():
            script = path / "scripts" / "video_watch.py"
            break
    if script is None and src:
        script = src / "scripts" / "video_watch.py"
    check_rc = run([sys.executable, str(script), "--check"], check=False) if script else 1

    bar = "=" * 64
    say("\n" + bar)
    say("VIDEO-WATCH IS READY" if env_ok and check_rc == 0 else "VIDEO-WATCH INSTALLED WITH PROBLEMS (see above)")
    say(bar)
    for label, path, status in results:
        say(f"  {label:<14} {path}  ({status})")
    say(f"  Environment    {VENV}")
    say("\nUse it (start a new agent session first):")
    say("  /video-watch <video link>                    watch, learn and create a skill")
    say("  /video-watch ask <video link> <question>     just answer a question")
    say("  /video-watch summary <video link>            just summarize")
    say(f"\nUpdate later: run this installer again.  Remove: add --uninstall.")
    say(bar)
    sys.exit(0 if env_ok and check_rc == 0 else 1)


if __name__ == "__main__":
    main()
