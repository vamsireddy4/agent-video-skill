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

Show the user what was created (read from disk):
    python3 scaffold_skill.py --card ~/.claude/skills/docker-multistage-deploy

List every skill learned from a video:
    python3 scaffold_skill.py --list
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import textwrap
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


def check_folder(folder: Path) -> tuple[list[str], list[str], list[str], dict, str]:
    """Return (problems, warnings, tips, frontmatter, text) for a skill folder."""
    problems, warnings, tips = [], [], []
    skill_md = folder / "SKILL.md"
    if not skill_md.exists():
        return [f"{skill_md} not found"], [], [], {}, ""
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
    if "## Source" not in text:
        tips.append("no '## Source' section; if this was learned from a video, add the link and credit the creator")
    return problems, warnings, tips, fm, text


def validate_folder(folder: Path) -> int:
    folder = folder.expanduser().resolve()
    problems, warnings, tips, _, _ = check_folder(folder)
    for p in problems:
        print(f"FAIL: {p}")
    for w in warnings:
        print(f"WARN: {w}")
    for t in tips:
        print(f"TIP: {t}")
    if not problems:
        print(f"OK: {folder.name} is a valid skill" + (" (see warnings)" if warnings else ""))
    return 1 if problems else 0


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def _agent_for(folder: Path) -> str:
    parts = folder.as_posix()
    for key, marker in (("Claude Code", "/.claude/"), ("Gemini CLI", "/.gemini/"), ("Cursor", "/.cursor/"),
                        ("GitHub Copilot", "/.github/"), ("Codex / shared agents folder", "/.agents/"),
                        ("Codex", "/.codex/")):
        if marker in parts + "/":
            return key
    return "custom folder (copy it into your agent's skills folder to use it)"


def show_card(folder: Path) -> int:
    """Print a confirmation card read from disk, so the user can see the skill really exists."""
    folder = folder.expanduser().resolve()
    if not (folder / "SKILL.md").exists():
        print("=" * 64)
        print("SKILL NOT CREATED")
        print(f"No SKILL.md found at {folder}")
        print("=" * 64)
        return 1
    problems, warnings, _, fm, text = check_folder(folder)
    name = fm.get("name", folder.name)
    status = "VALID" if not problems else "HAS PROBLEMS: " + "; ".join(problems)
    if not problems and warnings:
        status += " (warnings: " + "; ".join(warnings) + ")"
    src = re.search(r"Learned from:\s*(.+)", text)
    learned_on = re.search(r"Learned on:\s*([0-9-]+)", text)
    not_verified = _section(text, "Not verified")
    skip = {"__pycache__", "node_modules", "venv"}
    files = []
    for f in sorted(folder.rglob("*")):
        rel = f.relative_to(folder)
        if not f.is_file() or any(part.startswith(".") or part in skip for part in rel.parts):
            continue
        files.append(f"    {rel.as_posix()}  ({f.stat().st_size:,} bytes)")
    if len(files) > 25:
        files = files[:25] + [f"    ... and {len(files) - 25} more"]
    home = str(Path.home())
    shown_path = str(folder).replace(home, "~", 1) if str(folder).startswith(home) else str(folder)

    bar = "=" * 64
    print(bar)
    print(f"SKILL CREATED: {name}")
    print(bar)
    print(f"Saved at     : {shown_path}")
    print(f"For agent    : {_agent_for(folder)}")
    print(f"Status       : {status}")
    if src:
        print(f"Learned from : {src.group(1).strip()}")
    if learned_on:
        print(f"Learned on   : {learned_on.group(1)}")
    print("What it does :")
    for line in textwrap.wrap(fm.get("description", ""), 72):
        print("    " + line)
    print("Files:")
    print("\n".join(files) if files else "    (none)")
    print("How to use it:")
    print(f"    /{name}            (in Claude Code; other tools may use another prefix, e.g. ${name})")
    print("    or just ask for the task in your own words; the agent picks the skill from its description")
    print("    (start a new agent session first if the skill does not show up)")
    if not_verified and "TODO" not in not_verified:
        print("Not verified:")
        for line in not_verified.splitlines():
            if line.strip():
                print("    " + line.strip())
    print(bar)
    return 0 if not problems else 1


def list_learned(extra_dirs: list[str] | None) -> int:
    """List skills that were learned from videos (they carry a 'Learned from:' line)."""
    roots = {p[0] for p in AGENT_DIRS.values()} | {p[1].resolve() for p in AGENT_DIRS.values()}
    roots |= {Path(d).expanduser().resolve() for d in (extra_dirs or [])}
    found = []
    for root in sorted(roots, key=str):
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            text = skill_md.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"Learned from:\s*(.+)", text)
            if m:
                d = re.search(r"Learned on:\s*([0-9-]+)", text)
                found.append((skill_md.parent, m.group(1).strip(), d.group(1) if d else "?"))
    if not found:
        print("No skills learned from videos were found.")
        return 0
    print(f"{len(found)} skill(s) learned from videos:")
    for folder, src, day in found:
        print(f"- {folder.name}  [{day}]  {folder}")
        print(f"    from {src}")
    return 0


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
    print(f"  python3 {Path(__file__).resolve()} --card {folder}     # show the user the result")
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
    ap.add_argument("--card", metavar="FOLDER", help="Print a 'skill created' card for a skill folder and exit")
    ap.add_argument("--list", action="store_true", help="List skills learned from videos in all agent folders")
    ap.add_argument("--also", nargs="*", help="Extra folders to search with --list")
    args = ap.parse_args()

    if args.validate:
        sys.exit(validate_folder(Path(args.validate)))
    if args.card:
        sys.exit(show_card(Path(args.card)))
    if args.list:
        sys.exit(list_learned(args.also))
    if not args.name or not args.description:
        ap.error("creating a skill needs a name and --description (or use --validate FOLDER)")
    sys.exit(create(args))


if __name__ == "__main__":
    main()
