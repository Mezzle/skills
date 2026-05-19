# Mezzle Skills

Personal Claude Code skills. Distributed via [skills.sh](https://skills.sh) and copy-paste.

## Language

**Skill**:
A self-contained behavior loaded by Claude Code via a `SKILL.md` file with frontmatter (`name`, `description`). Lives at `skills/<bucket>/<name>/SKILL.md`.

**Bucket**:
A top-level grouping under `skills/` (`engineering`, `productivity`, `misc`, `personal`, `in-progress`, `deprecated`). Buckets determine promotion: only `engineering`, `productivity`, and `misc` skills appear in the README and plugin manifest.

**Daily log**:
A dated note in an Obsidian vault that records standup notes, TODOs, and outcomes for a single day. The `obsidian-daily-log` skill manages these.

## Relationships

- A **Skill** lives in exactly one **Bucket**
- The `.claude-plugin/plugin.json` manifest references **Skills** in promoted **Buckets** only
