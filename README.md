# agent-video-skill (`video-watch`)

An Agent Skill that lets any AI agent "watch" a video. Give it a link (YouTube, Vimeo, X,
Instagram, TikTok, news sites, direct `.mp4` / `.m3u8`) or a local file. It streams the video,
pulls out key frames and a timestamped transcript, and lines them up on one timeline. The agent
then looks at the frames with its own vision and reads the speech.

- No video is saved to disk; it is streamed.
- No AI API key is needed; the skill calls no model. Whatever agent runs it does the watching.
- Same folder works in Claude Code, OpenAI Codex, Gemini CLI, Cursor, GitHub Copilot and other
  tools that support the open Agent Skills (`SKILL.md`) format.

## Quick install

```bash
# Claude Code
git clone https://github.com/vamsireddy4/agent-video-skill ~/.claude/skills/video-watch

# OpenAI Codex, GitHub Copilot and other tools that read the shared folder
git clone https://github.com/vamsireddy4/agent-video-skill ~/.agents/skills/video-watch

# Gemini CLI
git clone https://github.com/vamsireddy4/agent-video-skill ~/.gemini/skills/video-watch

# Cursor
git clone https://github.com/vamsireddy4/agent-video-skill ~/.cursor/skills/video-watch
```

Then install ffmpeg and the Python packages (section 1 below). To update later, run `git pull`
inside that folder.

```
video-watch/
├── SKILL.md               instructions the agent reads
├── README.md              this file
├── requirements.txt
└── scripts/
    └── video_watch.py     the streaming + frames + transcript tool
```

## 1. Install the requirements

```bash
# ffmpeg (includes ffprobe)
brew install ffmpeg            # macOS
winget install ffmpeg          # Windows
sudo apt install ffmpeg        # Ubuntu / Debian

# Python packages
pip install -U -r requirements.txt     # run inside the skill folder
```

`faster-whisper` in requirements.txt is optional. It is only used when a video has no captions;
the first run downloads a speech model (about 150 MB for `base`).

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

Just ask your agent, for example:

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
| `out/sheets/*.jpg` | Contact sheets: six frames per image with timestamps, for agents with image limits |
| `out/transcript.txt` | Speech only, with timestamps |
| `out/timeline.json` | Everything above, machine-readable |

## How it works

1. **Find the stream.** Local files and direct media links go straight to ffmpeg. Web pages go
   through `yt-dlp -J`, which finds the real stream address without downloading.
2. **Key frames.** For videos up to 20 minutes, ffmpeg streams once and keeps a frame only when
   the picture changes (scene detection), then fills large gaps and drops duplicates. Longer
   videos use evenly spaced frames, grabbed by seeking inside the stream, so only small pieces
   are fetched.
3. **Speech.** Uploaded captions first, then auto-captions, then subtitle tracks inside the file,
   then Whisper on the streamed audio.
4. **Timeline.** Frames and speech are matched by timestamp and written to `timeline.md`.

## Limits

- DRM services (Netflix, Prime Video, Hotstar, Disney+) cannot be watched, by design.
- Frames are snapshots. Fast action between frames can be missed; re-run on a short window with
  `--mode interval --interval 1` for detail.
- Login-only videos need `--cookies-from-browser <browser>` and should only be used with your
  own account.
- Sites change; if a site stops working, update yt-dlp: `pip install -U yt-dlp`. YouTube may also
  need a JavaScript runtime such as Deno with recent yt-dlp versions.
- Respect each site's terms of service and the creator's rights.

## License

MIT, see [LICENSE](LICENSE).
