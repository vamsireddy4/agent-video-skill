# Learn a skill from a video

Use this when the user wants you to watch a video (usually a tutorial, walkthrough, talk or demo)
and turn what it teaches into a reusable Agent Skill, so that next time the task comes up you can
do it without watching the video again.

The output is a new skill folder that works in any agent supporting the Agent Skills format:

```
<skill-name>/
├── SKILL.md          when to use it + the method, in your own words
├── scripts/          runnable code or commands taken from the video (only if there are any)
└── references/       longer material the skill points to (optional)
```

Started with `/video-watch <link>` (or `/video-watch learn <link>`): run every step below without
waiting for approval between them, and watch the whole video from start to end. Use the skill name and `--agent` from the command if given; otherwise choose a short
task name and the agent you are running in (see "Commands" in SKILL.md).

## Step 1: Agree on the goal (one short question if unclear)

Before watching, know what the skill is for. "Make a skill from this video" can mean the whole
video or one technique inside it. If the user did not say, ask one question such as "Should the
skill cover the whole Docker deployment flow, or only the part about multi-stage builds?" If the
user is not around, take the main task the video teaches and say which one you chose.

## Step 2: Watch with the right settings

Tutorials put code, commands and settings on screen for only a few seconds, so scene detection
alone can miss them. Watch in two passes:

1. Overview pass (find the structure):
   ```bash
   python3 <video-watch>/scripts/video_watch.py "<url>" -o ./vw-overview
   ```
   Read `timeline.md` and the contact sheets. Note chapters and the time ranges where code,
   terminal output, config files or settings screens appear.

2. Detail pass on each of those ranges (read the screen):
   ```bash
   python3 <video-watch>/scripts/video_watch.py "<url>" -o ./vw-detail-1 \
       --start 06:10 --end 09:40 --mode interval --interval 2 --max-frames 120 --width 1600
   ```
   Open the individual frames (not only the contact sheets) to read code and commands; the wider
   `--width` keeps small text readable. Use `--interval 1` for fast typing.

For several videos on the same topic, run the overview pass on each and merge what you learn.

## Step 3: Extract the knowledge

Go through the timeline and fill this checklist (keep notes in a scratch file):

- **Goal:** what the method achieves, in one sentence.
- **When to use it / when not to:** the situations the video says it fits, and its warnings.
- **Prerequisites:** tools, versions, accounts, files, OS. Note versions shown on screen.
- **Steps, in order:** each step with the exact command, code or setting, and the timestamp where
  it appears, e.g. `[07:42] docker build -t app .`
- **Decisions and values:** every "set this to X because Y". The reason matters more than the value.
- **Mistakes and fixes:** errors shown on screen and how they were solved. These are often the most
  valuable part of a tutorial.
- **Checks:** how the video confirms it worked (an output, a page, a test).
- **Gaps:** anything skipped, cut, blurred or unreadable. Do not invent it; mark it as unknown.

Read code from the frames carefully. Compare the same code across several frames, because a
single blurred frame can turn `l` into `1` or drop a character. Cross-check commands against the
transcript ("now run npm install dash dash save dev") and against your own knowledge of the tool.

## Step 4: Write the skill

Create the folder with the scaffold script:

```bash
python3 <video-watch>/scripts/scaffold_skill.py docker-multistage-deploy \
    --description "Build and deploy a Node app with a multi-stage Docker image. Use when ..." \
    --source "https://www.youtube.com/watch?v=..." --source-title "Video title" \
    --agent claude
```

`--agent` picks where it is saved: `claude`, `codex`, `gemini`, `cursor`, `agents` (the shared
`~/.agents/skills` folder), or `--dir <path>` for anywhere else, such as a git repo. Then edit the
generated `SKILL.md`:

- **Name:** lowercase words joined by hyphens, describing the task (`docker-multistage-deploy`),
  not the video (`johns-docker-video`).
- **Description:** what it does and when to use it, with the words a user would actually say. The
  description decides when an agent picks the skill, so it is the most important line.
- **Body:** the method in imperative steps, in your own words, with the commands and values from
  Step 3. Keep the reasons ("use `--no-cache` here because the base image changes often").
- **Scripts:** put runnable code from the video into `scripts/` and reference it from SKILL.md,
  rather than pasting long code into the body. Prefer small, parameterised scripts over copies of
  the video's exact project.
- **Length:** keep SKILL.md under about 500 lines; move long details into `references/`.
- **Source:** keep the `Source` section the scaffold adds (video link, title, date learned), so the
  user can check the original and the creator gets credit.

Do not copy the video's narration or its full code verbatim. A skill captures the method; it is not
a transcript. Short commands and config lines are fine.

## Step 5: Verify before you call it done

- Run `python3 <video-watch>/scripts/scaffold_skill.py --validate <skill-folder>` to check the
  frontmatter (name format, description length, folder name).
- Run every script and command you can safely run (in a temporary folder, not inside the skill
  folder and never against the user's production systems). Fix anything the video got wrong or that is out of date, and note the fix
  in the skill ("The video uses `docker-compose`; current Docker uses `docker compose`").
- If you could not test something (needs cloud credentials, paid service, other OS), say so in the
  skill under a "Not verified" note and tell the user.
- Read the finished SKILL.md once as if you were a different agent seeing it for the first time:
  could you follow it without the video?

## Step 6: Show the user the skill

Print the confirmation card and show it to the user exactly as printed, in a code block:

```bash
python3 <video-watch>/scripts/scaffold_skill.py --card <skill-folder>
```

The card is read from disk, so it proves the skill exists. It shows the skill name, where it is
saved, which agent it is for, the description, the files, how to use it (`/<skill-name>` or plain
words), and the "Not verified" notes. Below the card, add one or two lines: what the skill teaches
and the first thing to try. Offer to install it for another agent too (copy the folder, or run the
scaffold with another `--agent`).

If no valid skill was saved, say "Skill was NOT created", give the reason, and what would fix it.
Never say a skill was created unless the card printed "SKILL CREATED".

All learned skills can be listed with `scaffold_skill.py --list`.

## Rules

- Only learn from videos the user points you to. Respect the creator: credit the source, write the
  method in your own words, and do not republish the video's full content.
- Never put secrets you saw on screen (API keys, passwords, tokens in a terminal) into the skill.
  Replace them with placeholders like `<YOUR_API_KEY>` and mention it.
- Do not run destructive commands from a video (deleting data, changing system settings,
  `curl ... | sh` from unknown sites) without the user's explicit OK.
