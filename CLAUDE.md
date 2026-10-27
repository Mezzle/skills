# Repo conventions

Skills live under `skills/<bucket>/<name>/SKILL.md`. Buckets:

- `engineering/` — daily code work
- `productivity/` — non-code workflow tools
- `misc/` — kept around but rarely used
- `personal/` — tied to a specific user's setup, not promoted
- `in-progress/` — drafts not yet ready to ship
- `deprecated/` — no longer used

Every skill in `engineering/`, `productivity/`, or `misc/` must have:

- A reference in the top-level `README.md` linking the skill name to its `SKILL.md`
- An entry in `.claude-plugin/plugin.json` under `"skills"`

Skills in `personal/`, `in-progress/`, and `deprecated/` must not appear in either.

## SKILL.md frontmatter

```yaml
---
name: <kebab-case slug, matches the directory name>
description: <one-line trigger description — written so Claude knows when to invoke it>
---
```

The `description` is what the model reads when deciding whether to load the skill. Phrase it as triggers: what the user says or does that should fire this skill. Lead with the verb (e.g. "Append to…", "Run when…").

## Style

- Terse. Cut filler.
- British English.
- Emoji only as status markers (✅, ❌, 🟡, 🤖), never in prose.
- File:line references where useful.
- Behaviours are universal; user-specific config (paths, templates) lives in instructions, not hardcoded values. Per-repo settings for the PR and review skills live in `.agents/config.yaml`; see `README.md`.
