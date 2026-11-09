---
name: video-watch
description: Watch a video from any URL (YouTube, Vimeo, X, Instagram, TikTok, news sites, direct .mp4/.m3u8 links) or a local file by streaming it into timestamped key frames plus a transcript, then answer questions about what is shown and said, or learn the method a tutorial teaches and save it as a new reusable Agent Skill. Use when the user shares a video link or file and asks to summarize it, explain it, find a moment, read on-screen text, code or slides, compare what was said with what was shown, or says "learn this", "make a skill from this video" or "turn this tutorial into a skill". Invoked as "/video-watch LINK" to watch the whole video, learn it and create a named skill, or "/video-watch ask LINK QUESTION" to only watch and answer.
---

# Video watch

You cannot play video directly, so this skill turns a video into things you can read and look at:
key frames (pictures, named by timestamp) and the speech (captions or Whisper transcript), lined up
on one timeline. The video is streamed, never saved to disk. No other AI model is called: you look
at the frames with your own image viewing and read the transcript yourself.

## Commands

Look at the words that came with the command (or the user's message) and pick the mode:

| What the user typed | Mode |
|---|---|
| `/video-watch <link or file> [more links] [skill-name] [--agent codex]` | **Learn** (default): watch the whole video, learn it, create a named skill, show the skill card |
| `/video-watch learn <link>` or `/video-watch skill <link>` | Learn (same as above) |
| `/video-watch ask <link> <question>` | Watch only: answer the question, no skill |
| `/video-watch summary <link>` | Watch only: summary with timestamps, no skill |
| Plain words without the command ("summarize this video", "what's at 4:12?") | Watch only |
| Plain words like "learn this video", "make a skill from this" | Learn |

Tools that invoke skills with a different prefix, such as `$video-watch`, use the same words after it.

### Learn mode (the default command)

Carry the whole job through without stopping, following `references/video-to-skill.md`:

1. **Watch and listen to the whole video.** Cover it from start to end, not just the opening: an
   overview pass over the full length with `--transcript audio --translate` (listens to the real
   audio in any language and adds an English translation when it is not English), then dense
   passes on every part where code, commands or settings are on screen (`--transcript none` there,
   since you already have the speech). For videos over 20 minutes, also go chapter by chapter (or every 10 minutes) so no
   section is skipped. Tell the user briefly that you are watching ("Watching 18:42 video...").
2. **Learn:** extract goal, prerequisites, steps, commands, decisions and reasons, mistakes and
   fixes, and how to check success.
3. **Name it:** use the skill name the user gave; otherwise pick a short, clear task name such as
   `docker-multistage-deploy` (lowercase words and hyphens, not the video title).
4. **Create** it with `scripts/scaffold_skill.py` in the skills folder of the agent you are running
   in (Claude Code: `--agent claude`, Codex: `codex`, Gemini CLI: `gemini`, Cursor: `cursor`, GitHub
   Copilot: `copilot`; if you cannot tell, `agents` and say so), unless the user gave `--agent`.
5. **Validate and test:** `scripts/scaffold_skill.py --validate <folder>`, then run the skill's
   scripts in a temporary folder (not inside the skill folder).
6. **Show the user the result.** Run `scripts/scaffold_skill.py --card <folder>` and show its
   output to the user exactly as printed, inside a code block. The card is read from disk, so it is
   proof the skill exists: name, where it is saved, which agent, what it does, its files, how to use
   it, and what was not verified. Then add one or two lines in your own words: what the skill
   teaches and the first thing to try with it.
7. If any step failed and no valid skill was saved, say clearly **"Skill was NOT created"**, give
   the reason and what the user can do (for example install ffmpeg, give a direct link). Never
   claim a skill exists unless the card printed "SKILL CREATED".

Ask a question first only when the goal is truly unclear, for example a 2-hour course covering many
unrelated topics ("Make one skill for the whole course, or one per topic?").

The user can see all learned skills any time with `scripts/scaffold_skill.py --list`.

## 1. Setup (automatic, once per computer)

Before the first video, run the check. It is fast and safe to run every time:

```bash
python3 <skill-folder>/scripts/video_watch.py --check
```

- If it ends with "Ready.", continue.
- If anything is marked MISS, or Whisper is missing, set everything up yourself without asking the
  user to do it by hand. Tell them in one line ("One-time setup: installing video tools, about
  2-5 minutes"), then run:
  ```bash
  python3 <skill-folder>/install.py --deps-only
  ```
  It needs no admin rights: it creates a private environment in `~/.video-watch` with yt-dlp,
  Pillow, faster-whisper and a bundled ffmpeg, and downloads the speech models. After that,
  `scripts/video_watch.py` uses that environment automatically. Run `--check` again to confirm.
- If Python itself is missing, ask the user to install Python 3 from python.org (or
  `brew install python`) and stop.
- If YouTube links fail and the check shows no JavaScript runtime, suggest installing Deno or
  Node.js.

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
| Denser motion strips for very fast action | `--motion-fps 15 --motion-frames 30` |
| Fastest run (skip the every-frame scan) | `--quick` |
| Speech only, no music / sound / tone analysis | `--no-audio-analysis` |
| More or fewer frames | `--max-frames 60`, or `--scene-threshold 0.2` (lower = more frames) |
| Long video (over 20 min) | Defaults to evenly spaced frames; raise `--max-frames` if your image budget allows |
| Always listen to the audio (best for non-English, mixed languages like Tenglish/Hinglish, or bad captions) | `--transcript audio` |
| Add an English translation of the speech | `--translate` |
| Tell it the spoken language instead of detecting it | `--lang te` (Telugu), `--lang hi`, `--lang ta`, ... |
| More accurate listening for Indian and other non-English languages | `--whisper-model-other medium` (or `large-v3`; slower) |
| Fastest, captions only, never listen | `--transcript captions` |
| Login-only video the user owns | `--cookies-from-browser chrome` (only when the user asks for it) |
| Direct stream URL without extension | `--direct` |

## Listening and languages

By default (`--transcript auto`) the script uses the creator's own captions if the video has them,
otherwise it **listens to the audio** with Whisper, and only falls back to the site's automatic
captions when listening is not possible. `--transcript audio` always listens.

- Whisper understands about 100 languages and detects the spoken one automatically
  (`timeline.md` shows "Spoken language: te (detected, 97% sure)"). It handles code-mixed speech
  such as Telugu-English reasonably well; pass `--lang` if detection picks the wrong language.
- For non-English speech the script automatically uses a larger model (`small` by default) because
  the smallest models are weak outside English. Use `--whisper-model-other medium` or `large-v3`
  for the best accuracy on Indian languages if the machine can handle it.
- `--translate` adds English lines marked `EN` under each original line, plus `transcript_en.txt`.
  Quote the original language when it matters (names, exact phrases) and use the English to be sure
  of the meaning.
- Listening covers speech only. Music, sound effects and tone of voice are not described, so do not
  claim them unless they are visible or spoken about.
- On a computer without a GPU, listening to a long video with `small` or bigger models can take
  several minutes; tell the user it is working.

## 3. Watch it

By default the script **reads every frame** of the video locally (one fast, low-resolution pass)
to measure motion and changes, then picks the frames worth your attention: every scene change,
every instant content change (new slide, new code line), the peak of every fast-motion stretch,
and enough evenly spread frames that no long stretch goes unseen. Pictures and sound are processed
at the same time. A 10-minute video usually takes well under a minute.

1. Read `timeline.md` first. It has the title, chapters, page description, an "Activity over
   time" line (calm, moderate, busy), and every key frame with what was said on screen at that
   moment. Lines marked `MOTION` and `SOUND` sit in the block where they happen.
2. Look at the pictures. Open the contact sheets in `sheets/` first: each one packs about six
   frames with the timestamp in the corner. Then open single files in `frames/` when you need
   detail, such as reading small text, a chart, or code.
3. **Fast motion:** for each stretch listed under "Fast motion", open its strip in `motion/`. A
   strip shows up to 18 frames from that stretch (about 8 per second), left to right and top to
   bottom, each with its time, so you can follow movement: what moved, which way, what happened.
4. **Sounds and music:** "Sounds and music" lists silence, likely music or tonal sound, noise /
   crowd / applause / effects, sudden loud sounds, and sound cues Whisper heard (for example
   "heard: applause"). These come from loudness and spectrum measurements, so name them as likely
   ("there seems to be music from 0:05 to 0:10"), not as certain facts.
5. **Tone cues:** speech lines may end with brackets such as `[very loud / shouting, higher pitch,
   fast]`, `[quiet / soft, slow]` or `[animated (pitch moves a lot)]`. They compare each line with
   the rest of the video. Combine them with the words and the pictures before saying how someone
   felt, and say it is an inference ("she sounds excited: louder, higher and faster here").
6. Use `timeline.json` if you need the numbers (motion scores, sound levels, timings).

If your image budget is small, look at contact sheets and motion strips only. Use `--quick` to
skip the every-frame scan when speed matters more than motion detail.

## 4. Answer (watch-only mode)

- Cite timestamps like `[04:12]` so the user can jump to the moment.
- Say whether something was shown (from a frame) or said (from the transcript). Combining them is
  the point: "At [04:12], while explaining pricing, the slide shows three plans: ...".
- Every frame was scanned, so fast action is not silently missed: check "Fast motion" and its
  strips. For an even closer look at one moment, re-run on that window, for example
  `--start 4:00 --end 4:10 --motion-fps 15 --motion-frames 30`, instead of guessing.
- If the speech source is "none found", tell the user your answer is based on visuals and page
  metadata only, and suggest installing faster-whisper so the audio can be listened to.
- Answer in the language the user writes in, even when the video is in another language.
- For long videos, summarize section by section (chapters, or every 10 minutes) before giving an
  overall summary.

## Learn a skill from a video

Learn mode (the default `/video-watch` command, see "Commands") follows
`references/video-to-skill.md`. In short:

1. Watch twice: an overview pass, then dense passes (`--mode interval --interval 2 --width 1600`)
   on the parts where code, commands or settings are on screen.
2. Extract the goal, prerequisites, ordered steps with exact commands, key decisions with their
   reasons, mistakes and fixes, and how success is checked.
3. Create the new skill with `scripts/scaffold_skill.py <name> --description "..." --source <url>
   --agent <claude|codex|gemini|cursor|agents>` and write the method in your own words, with
   runnable code in its `scripts/` folder.
4. Validate with `scripts/scaffold_skill.py --validate <folder>`, run what you safely can, then
   show the user `scripts/scaffold_skill.py --card <folder>` and what was not verified.

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
