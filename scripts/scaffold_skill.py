#!/usr/bin/env python3
"""
scaffold_skill.py - create or validate an Agent Skill folder (SKILL.md format).

Used by the "learn a skill from a video" workflow, but works for any skill.

Create:
    python3 scaffold_skill.py docker-multistage-deploy \
        --description "Build and deploy ... Use when ..." \
        --source "https://youtu.be/..." --source-title "Video title" \
        --agent claude            # or codex, gemini, cursor, agents, or --dir <path>

Validate:
    python3 scaffold_skill.py --validate ~/.claude/skills/docker-multistage-deploy
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

# Where each agent looks for skills (user-level, and project-level with --project).
# Folder conventions change between tool versions; --dir always wins.
AGENT_DIRS = {
    "claude": (Path.home() / ".claude" / "skills", Path(".claude") / "skills"),
    "codex": (Path.home() / ".agents" / "skills", Path(".agents") / "skills"),
    "gemini": (Path.home() / ".gemini" / "skills", Path(".gemini") / "skills"),
    "cursor": (Path.home() / ".cursor" / "skills", Path(".cursor") / "skills"),
    "copilot": (Path.home() / ".agents" / "skills", Path(".github") / "skills"),
    "agents": (Path.home() / ".agents" / "skills", Path(".agents") / "skills"),
}

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESC = 1024

TEMPLATE = """---
name: {name}
description: {description}
---

# {title}

{summary}

## When to use

- TODO: situations where this method fits (from the video, plus your own judgement)
- Do not use when: TODO (limits or warnings the video gives)

## Prerequisites

- TODO: tools and versions, accounts, files

## Steps

1. TODO: first step, with the exact command or setting
   ```bash
   # command
   ```
2. TODO

## Key decisions

- TODO: "set X to Y because Z" - keep the reason

## Common mistakes and fixes

- TODO: error -> fix

## Check that it worked

- TODO: the output, page or test that confirms success

## Not verified

- TODO: anything you could not test (or delete this section if everything was tested)

## Source

Learned from: [{source_title}]({source}){source_extra}
Learned on: {today}. The method is summarised in our own words; watch the original for the full
explanation and credit the creator when sharing.
"""


def validate_name(name: str) -> list[str]:
    errs = []
    if not name:
        errs.append("name is empty")
    elif len(name) > MAX_NAME:
        errs.append(f"name is {len(name)} characters; the limit is {MAX_NAME}")
    if name and not NAME_RE.match(name):
        errs.append("name must be lowercase letters, digits and single hyphens "
                    "(no spaces, no leading/trailing/double hyphens), e.g. docker-multistage-deploy")
    return errs


def validate_description(desc: str) -> list[str]:
    errs = []
    if not desc or not desc.strip():
        errs.append("description is empty")
    elif len(desc) > MAX_DESC:
        errs.append(f"description is {len(desc)} characters; the limit is {MAX_DESC}")
    if "<" in desc or ">" in desc:
        errs.append("description should not contain angle brackets (< or >)")
    return errs


def yaml_quote(text: str) -> str:
    """Quote a one-line YAML scalar only when needed."""
    text = " ".join(text.split())
    if re.search(r"[:#\[\]{}&*!|>'\"%@`]|^[-?]", text):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def parse_frontmatter(text: str) -> dict | None:
    m = re.match(r"^---\s*\n(.*?)\n---\s*(\n|$)", text, re.S)
    if not m:
        return None
    data: dict = {}
    key = None
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if km and not line.startswith((" ", "\t")):
            key, val = km.group(1), km.group(2).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
                val = val[1:-1].replace('\\"', '"') if val[0] == '"' else val[1:-1].replace("''", "'")
            data[key] = val
        elif key and line.startswith((" ", "\t")):
            data[key] = (data[key] + " " + line.strip()).strip() if data[key] not in ("|", ">", "|-", ">-") \
                else line.strip()
    return data


def validate_folder(folder: Path) -> int:
    folder = folder.expanduser().resolve()
    problems, warnings = [], []
    skill_md = folder / "SKILL.md"
    if not skill_md.exists():
        print(f"FAIL: {skill_md} not found")
        return 1
    text = skill_md.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if fm is None:
        problems.append("SKILL.md must start with YAML frontmatter between two '---' lines")
        fm = {}
    name, desc = fm.get("name", ""), fm.get("description", "")
    problems += validate_name(name)
    problems += validate_description(desc)
    if name and name != folder.name:
        problems.append(f"name '{name}' must match the folder name '{folder.name}'")
    body = text.split("---", 2)[-1] if fm else text
    lines = body.count("\n")
    if lines > 500:
        warnings.append(f"SKILL.md body is {lines} lines; consider moving detail into references/")
    todos = len(re.findall(r"\bTODO\b", text))
    if todos:
        warnings.append(f"{todos} TODO placeholder(s) still in SKILL.md")
    if re.search(r"(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|xox[bp]-[A-Za-z0-9-]{20,})", text):
        problems.append("SKILL.md seems to contain a secret (API key or token); replace it with a placeholder")
    for ref in re.findall(r"(?:scripts|references)/[A-Za-z0-9_.\-/]+", body):
        if not (folder / ref.rstrip(".,)")).exists():
            warnings.append(f"SKILL.md mentions {ref} but that file does not exist")
    tips = []
    if "## Source" not in text:
        tips.append("no '## Source' section; if this was learned from a video, add the link and credit the creator")

    for p in problems:
        print(f"FAIL: {p}")
    for w in warnings:
        print(f"WARN: {w}")
    for t in tips:
        print(f"TIP: {t}")
    if not problems:
        print(f"OK: {folder.name} is a valid skill" + (" (see warnings)" if warnings else ""))
    return 1 if problems else 0


def create(args) -> int:
    errs = validate_name(args.name) + validate_description(args.description)
    if errs:
        for e in errs:
            print(f"FAIL: {e}")
        return 1
    if args.dir:
        base = Path(args.dir).expanduser()
    else:
        user_dir, project_dir = AGENT_DIRS[args.agent]
        base = project_dir if args.project else user_dir
    folder = (base / args.name).resolve()
    if folder.exists() and any(folder.iterdir()) and not args.force:
        print(f"FAIL: {folder} already exists and is not empty (use --force to overwrite SKILL.md)")
        return 1
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "scripts").mkdir(exist_ok=True)
    (folder / "references").mkdir(exist_ok=True)

    title = args.title or args.name.replace("-", " ").capitalize()
    extra = ""
    if args.channel:
        extra += f" by {args.channel}"
    if args.extra_sources:
        extra += "".join(f"\nAlso: {s}" for s in args.extra_sources)
    (folder / "SKILL.md").write_text(TEMPLATE.format(
        name=args.name,
        description=yaml_quote(args.description),
        title=title,
        summary=args.summary or "TODO: one or two sentences on what this skill does and the result it produces.",
        source=args.source or "TODO-link",
        source_title=args.source_title or (args.source or "TODO: video title"),
        source_extra=extra,
        today=dt.date.today().isoformat(),
    ), encoding="utf-8")
    print(f"Created {folder}")
    print("Next: fill in the TODOs in SKILL.md, add scripts/, then run:")
    print(f"  python3 {Path(__file__).resolve()} --validate {folder}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Create or validate an Agent Skill (SKILL.md) folder.")
    ap.add_argument("name", nargs="?", help="Skill name, lowercase-with-hyphens")
    ap.add_argument("--description", help="What the skill does and when to use it (max 1024 chars)")
    ap.add_argument("--agent", choices=sorted(AGENT_DIRS), default="agents",
                    help="Which agent's skills folder to create it in (default: agents = ~/.agents/skills)")
    ap.add_argument("--project", action="store_true", help="Use the project-level folder in the current directory")
    ap.add_argument("--dir", help="Create inside this folder instead (e.g. a git repo)")
    ap.add_argument("--title", help="Heading for SKILL.md")
    ap.add_argument("--summary", help="One or two sentences for the top of SKILL.md")
    ap.add_argument("--source", help="Video URL the skill was learned from")
    ap.add_argument("--source-title", help="Video title")
    ap.add_argument("--channel", help="Creator / channel name")
    ap.add_argument("--extra-sources", nargs="*", help="Other videos or pages used")
    ap.add_argument("--force", action="store_true", help="Overwrite SKILL.md if the folder exists")
    ap.add_argument("--validate", metavar="FOLDER", help="Check an existing skill folder and exit")
    args = ap.parse_args()

    if args.validate:
        sys.exit(validate_folder(Path(args.validate)))
    if not args.name or not args.description:
        ap.error("creating a skill needs a name and --description (or use --validate FOLDER)")
    sys.exit(create(args))


if __name__ == "__main__":
    main()
