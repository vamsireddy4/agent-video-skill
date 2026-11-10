# merge-skills

Combine several skills on the same topic into **one complete skill**. Example: 5 SEO skills you made from 5 SEO videos become 1 SEO skill.

Claude reads every skill in full, removes duplicates, keeps the unique tips, asks you about any conflicts, and gives you the merged skill on a review card to save.

## How to use it

You don't need a special command. Just ask in plain words.

**Name the skills:**

```
Merge these 5 skills into one SEO skill: seo-keywords, seo-onpage,
seo-content, seo-technical, seo-backlinks.
```

**Or give only the topic:**

```
Merge all my SEO skills into one.
```

Claude finds every matching skill and shows you the list before merging.

## What happens

| Step | What Claude does |
|---|---|
| 1. Find | Finds the skills you named, or all skills on the topic, and confirms the list with you |
| 2. Read | Reads each skill fully: SKILL.md, reference files, scripts, examples |
| 3. Inventory | Lists every rule, step, checklist and example, grouped by stage of the work |
| 4. Dedupe | Says each idea once, using the most detailed version |
| 5. Conflicts | If skills disagree, keeps both with a condition, or asks you which one to keep |
| 6. Keep unique | Keeps a useful tip even if only one skill had it |
| 7. Write | Writes one clean skill in the order the work is done |
| 8. Check | Makes sure nothing was lost and nothing repeats |
| 9. Propose | Shows the merged skill on a review card. You click save |
| 10. Retire | Helps remove the old skills (see below) |

## Removing the old skills

The merge **does not delete** the old skills automatically.

| Where the old skills are | How they get removed |
|---|---|
| Saved in your Claude account | You delete them in **Customize → Skills** after saving the new one (about a minute) |
| Inside a plugin | Claude edits the plugin: removes the old skills, adds the merged one, repackages it |
| In a folder on your computer | Connect the folder and allow deletion. Claude removes them, or moves them to `_to_delete/` if deletion isn't allowed |

Always save the merged skill **first**, then remove the old ones.

## Good to know

- **It only knows what's written in the skills.** If your skills came from videos, anything in the videos that never got into a skill is missing. Share the original videos or notes too for a more complete result.
- **"Learning" means reading, not training.** Claude reads the skills in that chat and writes a new one. The saved skill is permanent and works in every future chat.
- **Size:** 20–30 skills is fine. If skills have very large reference folders, Claude focuses on the important parts.
