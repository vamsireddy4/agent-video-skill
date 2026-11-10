# merge-skills

**Learn from several skills, then create one new skill from what was learned.** Example: 5 SEO skills you made from 5 SEO videos become 1 SEO skill.

The agent doesn't just glue the old skills together. It first **studies** every skill and writes its own learning notes: the goal, the steps, the reason behind each rule, and how all the skills fit into one workflow. It checks that it really understood. Only then does it **write a new skill from that understanding**, in one voice, with no duplicates and every conflict resolved.

## How to use it

You don't need a special command. Just ask in plain words.

**Name the skills:**

```
Merge these 5 skills into one SEO skill: seo-keywords, seo-onpage,
seo-content, seo-technical, seo-backlinks.
```

**Or give only the topic:**

```
Learn from all my SEO skills and make one.
```

The agent finds every matching skill and shows you the list before starting.

## What happens

### Phase 1: Learn

| Step | What the agent does |
|---|---|
| 1. Find | Finds the skills you named, or all skills on the topic, and confirms the list with you |
| 2. Study | Reads each skill fully (SKILL.md, reference files, scripts, examples) and works out **why** each rule exists |
| 3. Notes per skill | Writes learning notes in its own words: goal, method, principles with reasons, exact details, what's unique |
| 4. Connect | Finds the core concepts, builds **one end-to-end workflow**, and lists duplicates, conflicts and gaps |
| 5. Self-check | Plans 3 realistic tasks using only its notes. If something is missing, it goes back and studies again. Then it tells you what it learned |

### Phase 2: Create

| Step | What the agent does |
|---|---|
| 6. Conflicts | Keeps both sides with a condition, or asks you which one to keep |
| 7. Design | Plans the new skill around the one workflow, not the old skills' outlines |
| 8. Write | Writes the skill from its notes, in its own words. Exact commands and numbers stay exact |
| 9. Test | Checks nothing was lost, then runs the same 3 tasks using only the new skill |
| 10. Propose | Shows the new skill on a review card. You click save |
| 11. Retire | Helps remove the old skills (see below) |

## Removing the old skills

The old skills are **not deleted automatically**.

| Where the old skills are | How they get removed |
|---|---|
| Saved in your Claude account | You delete them in **Customize → Skills** after saving the new one (about a minute) |
| Inside a plugin | The agent edits the plugin: removes the old skills, adds the new one, repackages it |
| In a folder on your computer | Connect the folder and allow deletion. The agent removes them, or moves them to `_to_delete/` if deletion isn't allowed |

Always save the new skill **first**, then remove the old ones.

## Good to know

- **"Learning" means studying, not training.** The agent studies the skills in that chat and writes down what it understood. The model itself doesn't change. What lasts is the new skill, which works in every future chat.
- **It only knows what's in the skills.** If your skills came from videos, anything in the videos that never got into a skill is missing. Share the original videos or notes too and the agent will study them in Phase 1.
- **Gaps are reported, not invented.** If no skill covers a part of the workflow, the agent tells you instead of making up advice.
- **Size:** 20–30 skills is fine. If skills have very large reference folders, the agent focuses on the important parts.
