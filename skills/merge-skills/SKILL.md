---
name: merge-skills
description: Learn from several existing skills on one topic (e.g. 5 SEO skills) and create one new combined skill from what was learned, with no duplicates and conflicts resolved. Use when asked to merge, combine, consolidate or learn from several skills.
---

# Merge skills

Learn a topic from several skills first, then write **one new skill from that understanding**. Do not glue the old skills together section by section. The new skill should read like it was written by someone who has mastered the topic, not like five documents stapled together.

This works in two phases, and Phase 2 never starts until Phase 1 passes its check:

1. **Learn:** study every source skill and write learning notes in your own words.
2. **Create:** design and write the new skill from those notes, then test it.

"Learning" here means studying the skills in this session and writing down what was understood. The model itself is not retrained. What lasts is the new skill.

## How to ask

The user can name the skills or just the topic:

- "Merge these 5 skills into one SEO skill: seo-keywords, seo-onpage, seo-content, seo-technical, seo-backlinks."
- "Learn from all my SEO skills and make one."

No special command is needed.

---

## Phase 1: Learn

### 1. Find the source skills
- If the user named them, use those names.
- If they gave only a topic, list the user's skills (ListSkills with the topic as keyword, plus the skills listed in the session) and pick every skill on that topic. Show the list and confirm it before starting.
- If a named skill can't be found, say which one and ask for its exact name or the file.

### 2. Study each skill completely
- Load each one with the Skill tool, or read its SKILL.md.
- Also read its reference files, scripts, templates and examples. Run scripts only to understand what they do, in a temporary folder.
- Read slowly enough to understand **why** each step or rule exists, not just what it says.

### 3. Write learning notes for each skill
Create a notes file in the working directory (e.g. `learning-notes.md`). For each source skill, write in your own words:

- **Goal:** what this skill helps someone achieve.
- **Method:** the steps, in order.
- **Principles:** the rules, each with the reason behind it. If the skill gives no reason, work it out and mark it as your inference.
- **Exact details:** commands, numbers, thresholds, templates and examples, copied exactly.
- **Unique value:** what this skill teaches that the others may not.

### 4. Connect what you learned across skills
In the same notes file, write the big picture:

- **Core concepts:** the ideas that appear across several skills. These become the backbone of the new skill.
- **One workflow:** how the skills fit together into a single end-to-end process, in the order the work is really done (for SEO, for example: research → planning → writing → on-page → technical → links → measuring). Note where one skill's output feeds another's input.
- **Duplicates:** the same idea said in different skills. Note which version is the clearest and most detailed.
- **Conflicts:** where skills disagree. For each, write both sides, their sources, and whether the difference depends on situation (e.g. new site vs. established site).
- **Gaps:** important parts of the workflow none of the skills cover. Note them, but do not fill them with invented advice.

### 5. Check your understanding before moving on
Write 3 realistic tasks someone would bring to this topic (e.g. "rank a new local bakery site", "fix a blog that lost traffic", "plan content for a SaaS launch"). For each, plan how to do it **using only your notes**.

- If a plan needs something that is in a source skill but missing from your notes, the notes are incomplete. Go back and add it.
- If you can't explain why a principle matters, re-read that skill.
- Only move to Phase 2 when all 3 plans work from the notes alone.

Give the user a short summary of what you learned: the core concepts, the one workflow, and the conflicts you found.

---

## Phase 2: Create

### 6. Resolve conflicts
- If a conflict depends on situation, keep both sides with the condition ("for a new site, do A; for an established site, do B").
- Otherwise, show the user each conflict with both sides and their sources, and ask which to keep. Ask all conflicts together in one question set.

### 7. Design the new skill from your notes
Plan the structure from the **one workflow** in step 4, not from the old skills' outlines.

- Name: short kebab-case for the topic (e.g. `seo`), unless the user gave one.
- Description: one sentence covering what it does and when to use it, including the trigger phrases from all the source skills' descriptions.
- Body order: purpose → when to use → the workflow step by step → principles (with reasons) → checklists → examples.

### 8. Write it in your own words
- Write from the notes, as one voice. Do not copy sections across from the old skills.
- Keep exact commands, numbers, thresholds and templates exactly as the source had them.
- Each idea appears once, in the clearest and most detailed version.
- Keep every unique tip unless it is clearly wrong or out of scope.
- Keep the SKILL.md focused. Put long checklists, templates or reference tables in separate reference files and point to them.
- Plain, direct language.

### 9. Test the new skill
- Coverage: every item in the notes is either in the new skill or dropped on purpose (duplicate, or the user's conflict choice).
- No idea appears twice, and no contradictions are left.
- Run the 3 tasks from step 5 again, this time using **only the new skill**. Each should be as complete as it was from the notes. If not, fix the skill.

### 10. Propose it
- Use propose_skills to show the new skill on a review card. The user saves it from the card.
- In the reply, say in a few lines: which skills it learned from, the core concepts it's built around, how many duplicates were folded in, and how each conflict was resolved.

### 11. Retire the old skills
The old skills are not deleted automatically. Do this only after the user has saved the new skill.

- **Skills saved in the user's account:** these can't be deleted from here. Tell the user to delete them in Customize → Skills.
- **Skills inside a plugin:** use the cowork-plugin skill to remove the old skills from the plugin, add the new one, and repackage it.
- **Skill files in a folder on the user's computer:** with that folder connected and delete permission granted, delete the old skill folders. If deletion isn't allowed, move them into a `_to_delete/` folder and tell the user.

## Limits

- The new skill only knows what was in the source skills. If they came from videos or articles, ideas that never made it into the skills are missing. If the user has the original sources, study them too in Phase 1.
- Gaps found in step 4 are reported, not filled with made-up advice.
