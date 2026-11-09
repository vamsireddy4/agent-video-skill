---
name: video-watch
description: Watch a video from any URL (YouTube, Vimeo, X, Instagram, TikTok, news sites, direct .mp4/.m3u8 links) or a local file by streaming it into timestamped key frames plus a transcript, then answer questions about what is shown and said. Use when the user shares a video link or file and asks to summarize it, explain it, find a moment, read on-screen text or slides, or compare what was said with what was shown.
---

# Video watch

You cannot play video directly, so this skill turns a video into things you can read and look at:
key frames (pictures, named by timestamp) and the speech (captions or Whisper transcript), lined up
on one timeline. The video is streamed, never saved to disk. No other AI model is called: you look
at the frames with your own image viewing and read the transcript yourself.

## 1. Check the tools (once per machine)

The script needs `ffmpeg` and `ffprobe`. Web pages also need `yt-dlp`. Check with:

```bash
ffmpeg -version && yt-dlp --version
```

If something is missing, tell the user and offer to install it:

- ffmpeg: `brew install ffmpeg` (macOS), `winget install ffmpeg` (Windows), `sudo apt install ffmpeg` (Linux)
- Python packages: `pip install -U yt-dlp pillow` (Pillow makes contact sheets)
- Optional speech-to-text for videos with no captions: `pip install faster-whisper`

## 2. Run the script

`scripts/video_watch.py` is inside this skill's folder. Use its full path:

```bash
python3 <skill-folder>/scripts/video_watch.py "<video URL or file path>" -o ./video-watch-out
```

It prints a short JSON summary at the end (frame count, speech source, and the path to read first).
Progress messages go to stderr. Scene scans read the whole stream, so a 20-minute video can take a
few minutes; let it finish.

Useful options:

| Need | Option |
|---|---|
| Only part of the video | `--start 12:30 --end 15:00` |
| More detail on a moment | `--start 4:00 --end 4:30 --mode interval --interval 1` |
| More or fewer frames | `--max-frames 60`, or `--scene-threshold 0.2` (lower = more frames) |
| Long video (over 20 min) | Defaults to evenly spaced frames; raise `--max-frames` if your image budget allows |
| Captions in another language | `--lang te` (Telugu), `--lang hi`, ... |
| Force speech-to-text | `--transcript whisper --whisper-model small` |
| Login-only video the user owns | `--cookies-from-browser chrome` (only when the user asks for it) |
| Direct stream URL without extension | `--direct` |

## 3. Watch it

1. Read `timeline.md` first. It has the title, chapters, page description, and every key frame
   with the speech that happened while that frame was on screen.
2. Look at the pictures. Open the contact sheets in `sheets/` first: each one packs about six
   frames with the timestamp in the corner, so you see the whole video in a few images. Then open
   single files in `frames/` when you need detail, such as reading small text, a chart, or code.
   If your image budget is small, prefer contact sheets; if you can view many images, open the
   individual frames.
3. Use `timeline.json` if you need to process the data programmatically.

## 4. Answer

- Cite timestamps like `[04:12]` so the user can jump to the moment.
- Say whether something was shown (from a frame) or said (from the transcript). Combining them is
  the point: "At [04:12], while explaining pricing, the slide shows three plans: ...".
- Frames are snapshots, not continuous video. If the user asks about something that could happen
  between two frames (fast action, a quick gesture), say so and re-run on that window with
  `--mode interval --interval 1` instead of guessing.
- If the speech source is "none found", tell the user your answer is based on visuals and page
  metadata only, and suggest installing faster-whisper.
- For long videos, summarize section by section (chapters, or every 10 minutes) before giving an
  overall summary.

## 5. Limits and rules

- DRM-protected services (Netflix, Prime Video, Hotstar, Disney+ and similar) cannot be watched.
  Do not try to work around DRM or copy protection.
- Only use cookies or a logged-in browser when the user explicitly asks, and only for their own
  account.
- Do not save the full video to disk. The script streams on purpose.
- If yt-dlp says the URL is unsupported and you have a browser tool, you can fall back to opening
  the page, seeking the video element (`video.currentTime = t`) and screenshotting it at a few
  timestamps. Otherwise ask the user for a direct video link or file.
- If YouTube fails with a JavaScript or "sign in to confirm" error, update yt-dlp first
  (`pip install -U yt-dlp`); recent yt-dlp versions may also need a JavaScript runtime such as
  Deno installed for YouTube.
- The output folder can be deleted when the user is done (`rm -rf ./video-watch-out`).
