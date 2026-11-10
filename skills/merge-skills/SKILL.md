---
name: merge-skills
description: Merge several existing skills on one topic (e.g. 5 SEO skills) into one combined skill, removing duplicates and resolving conflicts. Use when asked to merge, combine or consolidate skills.
---

# Merge skills

Turn several skills on the same topic into one complete skill, so nothing useful is lost and nothing is said twice.

## How to ask

The user can name the skills or just the topic:

- "Merge these 5 skills into one SEO skill: seo-keywords, seo-onpage, seo-content, seo-technical, seo-backlinks."
- "Merge all my SEO skills into one."

No special command is needed.

## Steps

### 1. Find the source skills
- If the user named them, use those names.
- If they gave only a topic, list the user's skills (ListSkills with the topic as keyword, plus the skills listed in the session) and pick every skill on that topic. Show the user the list and confirm it before merging.
- If a named skill can't be found, say which one and ask for its exact name or the file.

### 2. Read every source skill completely
- Load each one with the Skill tool, or read its SKILL.md file.
- Also read its reference files, scripts and examples, not just the main file.
- For each skill, note: what it's for, its steps, its rules (do / don't), checklists, templates, examples, numbers and thresholds, and tools it depends on.

### 3. Build one inventory
Put everything from step 2 into one list, grouped by stage of the work (for SEO, for example: research → planning → writing → on-page → technical → links → measuring).

For each item, mark which source skill(s) it came from.

### 4. Remove duplicates
- When two or more skills say the same thing, keep it once, in the clearest and most specific wording.
- When one version has more detail (an exact number, an example), keep the detailed one.

### 5. Resolve conflicts
- When skills disagree (one says do X, another says don't), do not silently pick one.
- If the difference depends on situation, keep both with the condition ("for a new site, do A; for an established site, do B").
- Otherwise, list the conflicts for the user with each side and its source, and ask which to keep. Ask all conflicts together in one question set.

### 6. Keep the unique ideas
A rule or tip that appears in only one source skill still goes in, unless it is clearly wrong or out of scope. Nothing useful is dropped just because it appeared once.

### 7. Write the merged skill
- Name: short kebab-case for the topic (e.g. `seo`), unless the user gave one.
- Description: one sentence covering when to use it, including the trigger phrases from all the source skills' descriptions.
- Body order: purpose → when to use → steps in the order the work is done → rules → checklists → examples.
- Keep the SKILL.md focused. Put long checklists, templates or reference tables in separate reference files and point to them.
- Write in plain, direct language.

### 8. Check before proposing
- Every item in the inventory is either in the merged skill or was dropped on purpose (duplicate, or the user's conflict choice).
- No rule appears twice.
- No leftover contradictions.

### 9. Propose it
- Use propose_skills to show the merged skill on a review card. The user saves it from the card.
- In the reply, say in a few lines: which skills were merged, how many duplicates were removed, and which conflicts were resolved and how.

### 10. Retire the old skills
The merge does not delete the source skills automatically.

- **Skills saved in the user's account:** these can't be deleted from here. Tell the user to delete them in Customize → Skills after saving the new one.
- **Skills inside a plugin:** use the cowork-plugin skill to remove the old skills from the plugin, add the merged one, and repackage it.
- **Skill files in a folder on the user's computer:** with that folder connected and delete permission granted, delete the old skill folders. If deletion isn't allowed, move them into a `_to_delete/` folder and tell the user.

Always do this step only after the user has saved the merged skill.

## Limits

- The merged skill only knows what was written in the source skills. If the source skills came from videos or articles, ideas that never made it into the skills are missing. If the user has the original sources, read them too.
- "Learning" here means reading the skills in this session and writing a new one. The saved skill is permanent; nothing else changes.
