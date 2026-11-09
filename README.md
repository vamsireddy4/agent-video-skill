# agent-video-skill (`video-watch`)

An Agent Skill that lets any AI agent "watch" a video. Give it a link (YouTube, Vimeo, X,
Instagram, TikTok, news sites, direct `.mp4` / `.m3u8`) or a local file. It streams the video,
pulls out key frames and a timestamped transcript, and lines them up on one timeline. The agent
then looks at the frames with its own vision and reads the speech.

- No video is saved to disk; it is streamed.
- No AI API key is needed; the skill calls no model. Whatever agent runs it does the watching.
- It can also **learn from a video**: watch a tutorial and save what it teaches as a new,
  reusable skill (see "Learn a skill from a video" below).
- Same folder works in Claude Code, OpenAI Codex, Gemini CLI, Cursor, GitHub Copilot and other
  tools that support the open Agent Skills (`SKILL.md`) format.

## Quick install (one command, everything automatic)

**macOS / Linux**

```bash
curl -fsSL https://raw.githubusercontent.com/vamsireddy4/agent-video-skill/main/install.sh | sh
```

**Windows (PowerShell)**

```powershell
irm https://raw.githubusercontent.com/vamsireddy4/agent-video-skill/main/install.py | python -
```

The installer needs only Python 3.9+ and no admin rights. It:

1. finds the AI agents on your computer (Claude Code, Codex, Gemini CLI, Cursor) and installs the
   skill into each one's skills folder;
2. creates a private environment in `~/.video-watch` with yt-dlp, Pillow, faster-whisper and a
   bundled ffmpeg (your own ffmpeg is used if you already have one);
3. downloads the Whisper speech models so the first video is fast;
4. runs a self-check and prints where everything went.

Run the same command again to update. Options: `--agents claude,codex` to choose agents,
`--no-models` to skip the model download, `--uninstall` to remove everything.

**Prefer git clone?** That works too. Clone into your agent's skills folder:

```bash
git clone https://github.com/vamsireddy4/agent-video-skill ~/.claude/skills/video-watch
```

Git never runs code on clone, so the setup happens on first use instead: the first time you use
`/video-watch`, the agent runs `scripts/video_watch.py --check`, sees what is missing and runs
`install.py --deps-only` for you. You can also run `python3 install.py` inside the clone yourself.

```
video-watch/
├── SKILL.md               instructions the agent reads
├── README.md              this file
├── requirements.txt
├── install.py             one-command installer (also used for first-use setup)
├── install.sh             macOS / Linux wrapper for install.py
├── references/
│   └── video-to-skill.md  step-by-step guide for learning a skill from a video
└── scripts/
    ├── video_watch.py     the streaming + frames + transcript tool
    └── scaffold_skill.py  creates and validates new skill folders
```

## 1. Requirements (handled by the installer)

You only need Python 3.9 or newer. The installer or the first-use setup installs the rest into
`~/.video-watch`: yt-dlp, Pillow, faster-whisper and a bundled ffmpeg. Check any time:

```bash
python3 ~/.claude/skills/video-watch/scripts/video_watch.py --check
```

`faster-whisper` lets the agent **listen to the audio** in about 100 languages (Telugu, Hindi,
Tamil, Kannada, Malayalam, English, Spanish, ...). The installer downloads the `base` (about
150 MB, English) and `small` (about 500 MB, other languages) speech models. For YouTube, recent
yt-dlp versions may also need a JavaScript runtime: install Deno or Node.js if YouTube links fail.

To install manually instead: `brew install ffmpeg` / `winget install ffmpeg` /
`sudo apt install ffmpeg`, then `pip install -U -r requirements.txt`.

## 2. Put the folder where your agent looks for skills

| Agent | Folder (for all your projects) | Folder (one project only) |
|---|---|---|
| Claude Code | `~/.claude/skills/video-watch/` | `.claude/skills/video-watch/` |
| OpenAI Codex | `~/.agents/skills/video-watch/` or `~/.codex/skills/video-watch/` | `.agents/skills/video-watch/` |
| Gemini CLI | `~/.gemini/skills/video-watch/` | `.gemini/skills/video-watch/` or `.agents/skills/video-watch/` |
| Cursor | `~/.cursor/skills/video-watch/` | `.cursor/skills/video-watch/` |
| GitHub Copilot | | `.github/skills/video-watch/` or `.agents/skills/video-watch/` |

Skill folder locations change between tool versions, so check your tool's docs if it does not pick
the skill up. A tool that does not support skills can still use it: point it at `SKILL.md` and ask
it to follow the instructions.

Example (macOS / Linux, Claude Code):

```bash
git clone https://github.com/vamsireddy4/agent-video-skill ~/.claude/skills/video-watch
pip install -U -r ~/.claude/skills/video-watch/requirements.txt
```

On Windows, use `python` instead of `python3` and a path such as
`%USERPROFILE%\.claude\skills\video-watch`.

## 3. Use it

### Commands

| Command | What happens |
|---|---|
| `/video-watch <link>` | Watches the **whole** video, learns it, **creates a new skill** with a clear name, and shows a "SKILL CREATED" card |
| `/video-watch <link> docker-deploy --agent codex` | Same, with your own skill name and target agent |
| `/video-watch ask <link> <question>` | Only watches and answers your question (no skill) |
| `/video-watch summary <link>` | Only watches and summarizes with timestamps (no skill) |

`learn` and `skill` also work (`/video-watch learn <link>`). In tools that use another prefix
(for example `$video-watch`), type the same words after it.

When a skill is created you see a card like this, read straight from disk:

```
================================================================
SKILL CREATED: flask-health-api
================================================================
Saved at     : ~/.claude/skills/flask-health-api
For agent    : Claude Code
Status       : VALID
Learned from : [Flask health API tutorial](https://youtu.be/...)
Learned on   : 2026-11-09
What it does :
    Create and run a minimal Flask API with a /health endpoint on a free
    port. Use when the user wants a quick Flask server, a health-check
    endpoint, or a Python API starter.
Files:
    SKILL.md  (1,142 bytes)
    scripts/app.py  (111 bytes)
    scripts/run.sh  (330 bytes)
How to use it:
    /flask-health-api            (in Claude Code; other tools may use another prefix, e.g. $flask-health-api)
    or just ask for the task in your own words; the agent picks the skill from its description
    (start a new agent session first if the skill does not show up)
Not verified:
    - macOS AirPlay port conflict (tested on Linux only)
================================================================
```

If something fails, the agent says "Skill was NOT created" and why. See every skill learned so far:

```bash
python3 ~/.claude/skills/video-watch/scripts/scaffold_skill.py --list
```

### Or just ask


- "Watch https://www.youtube.com/watch?v=... and summarize it with timestamps"
- "What was on the slide when they talked about pricing in this video: <link>"
- "Read the code shown at 12:30 in this tutorial"
- "Watch demo.mp4 and list every feature they showed"

Or run the tool yourself:

```bash
python3 scripts/video_watch.py "https://vimeo.com/123456" -o out
python3 scripts/video_watch.py lecture.mp4 --start 10:00 --end 20:00 -o out
python3 scripts/video_watch.py "<url>" --mode interval --interval 5 --max-frames 80 -o out
```

Output:

| File | What it is |
|---|---|
| `out/timeline.md` | Read this first: each key frame with what was said while it was on screen |
| `out/frames/*.jpg` | Key frames, named by timestamp (`frame_0003_00h04m12s.jpg`) |
| `out/motion/*.jpg` | Motion strips: the fast parts, frame by frame |
| `out/sheets/*.jpg` | Contact sheets: six frames per image with timestamps, for agents with image limits |
| `out/transcript.txt` | Speech only, with timestamps, in the spoken language |
| `out/transcript_en.txt` | English translation of the speech (with `--translate`) |
| `out/timeline.json` | Everything above, machine-readable |

## Learn a skill from a video

Type `/video-watch <link>`, or ask your agent something like:

- "Watch this Docker tutorial and make a skill out of it: <link>"
- "Learn the deployment steps from this video and save them as a Codex skill"

The agent then:

1. Watches an overview pass, then dense passes (`--mode interval --interval 2`) where code or
   commands are on screen, so short-lived code is not missed.
2. Pulls out the goal, prerequisites, ordered steps with exact commands, key decisions with their
   reasons, mistakes and fixes, and how to check it worked.
3. Creates the new skill folder in the right agent's skills directory:
   ```bash
   python3 scripts/scaffold_skill.py docker-multistage-deploy \
       --description "Build and deploy ... Use when ..." \
       --source "https://youtu.be/..." --source-title "Video title" --agent claude
   ```
4. Writes the method in its own words (with runnable scripts), validates it, runs what it safely
   can, and shows you the "SKILL CREATED" card (`scaffold_skill.py --card <folder>`).

Validate any skill folder:

```bash
python3 scripts/scaffold_skill.py --validate ~/.claude/skills/docker-multistage-deploy
```

`--agent` accepts `claude`, `codex`, `gemini`, `cursor`, `copilot` and `agents` (the shared
`~/.agents/skills` folder); `--project` uses the project-level folder, and `--dir <path>` saves
anywhere, such as a git repo. Learned skills keep a Source section with the video link so the
creator gets credit. Code read from video frames can contain small errors, which is why the
workflow tests before it calls a skill done.

## Listening to the audio, in any language

| Option | What it does |
|---|---|
| *(default)* `--transcript auto` | Uses the creator's captions if there are any, otherwise **listens to the audio**, and only then falls back to the site's auto-captions |
| `--transcript audio` | Always listens to the audio (best for non-English, Tenglish/Hinglish, or bad captions). Learn mode uses this |
| `--translate` | Adds an English translation under each spoken line (`EN` lines and `transcript_en.txt`) |
| `--lang te` | Tells it the spoken language instead of detecting it |
| `--whisper-model-other medium` | More accurate (slower) model for non-English speech; `large-v3` is the most accurate |
| `--transcript captions` | Never listens; fastest |

The spoken language is detected automatically and shown in `timeline.md`, for example
`Spoken language: te (detected, 97% sure)`. English uses the small `base` model; other languages
automatically switch to `small`, because the smallest models are weak outside English.
Listening covers speech only; music and sound effects are not described.

## How it works

1. **Find the stream.** Local files and direct media links go straight to ffmpeg. Web pages go
   through `yt-dlp -J`, which finds the real stream address without downloading.
2. **Every frame read, the right frames shown.** One fast, low-resolution pass reads every frame
   (about 15,000 frames of a 10-minute video in under 20 seconds) and measures scene changes,
   instant content changes and motion. Full-size frames are then grabbed only at scene changes,
   new slides or code lines, the peak of each fast-motion stretch, and evenly spread points so no
   long stretch goes unseen. Fast stretches also get a **motion strip**: up to 18 frames at about
   8 per second in one image, so the agent can follow the movement. `--quick` skips the scan.
3. **Speech.** Creator-uploaded captions or subtitle tracks inside the file first, then Whisper
   listening to the streamed audio (language detected automatically, optional English
   translation), then the site's auto-captions as a last resort.
4. **Sound and tone.** The same audio stream is measured for silence, likely music, noise / crowd
   / applause / effects and sudden loud sounds, and each spoken line gets tone cues from its
   loudness, pitch and speed compared with the rest of the video (`[loud, higher pitch, fast]`).
5. **Timeline.** Frames, motion, sounds and speech are matched by timestamp and written to
   `timeline.md`. Pictures and sound are processed at the same time to keep it fast.

## Limits

- DRM services (Netflix, Prime Video, Hotstar, Disney+) cannot be watched, by design.
- The AI looks at selected frames and motion strips, not all of them: every frame is measured
  locally, but sending thousands of images to a model would be slow and expensive. For a closer
  look at one moment use `--start/--end` with `--motion-fps 15 --motion-frames 30`.
- Sound and tone labels come from measurements (loudness, pitch, spectrum), not from a sound
  recognition model: "likely music" and "loud, higher pitch" are hints, not certainties.
- Login-only videos need `--cookies-from-browser <browser>` and should only be used with your
  own account.
- Sites change; if a site stops working, update yt-dlp: `pip install -U yt-dlp`. YouTube may also
  need a JavaScript runtime such as Deno with recent yt-dlp versions.
- Respect each site's terms of service and the creator's rights.

## License

MIT, see [LICENSE](LICENSE).
