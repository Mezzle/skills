---
name: obsidian-daily-log
description: Append outcomes, TODOs, and notes to today's Obsidian daily log. Use when the user says "update today's log", "log what I did", "add to my daily note", asks "what did I do today?", or when a discrete piece of work lands and is worth recording. Reads the most recent existing daily note as the canonical template, appends rather than overwrites, dedups, and never touches dataview blocks.
---

# Obsidian Daily Log

A discipline for keeping an Obsidian daily note current without corrupting it. The skill is generic — your vault layout, frontmatter, and section list are learned from your own most recent daily note, which is treated as the canonical template.

## Setup

Tell the skill once where your daily notes live by adding a memory or by setting the path in your project `CLAUDE.md`:

```
Obsidian daily notes live at: <absolute path to vault folder containing daily notes>
Daily note filename pattern: <e.g. YYYY/MMMM/YYYY-MM-DD.md>
```

If no path is set, ask the user before doing anything else. Never guess.

## The canonical reference

**Before any write, read the most recent existing daily note in the vault.** That file is the single source of truth for:

- Frontmatter shape (tags, date format, aliases)
- Section order and headings
- Writing voice and density
- Whether dataview / templater / other rendered blocks are present

The skill does not ship with a hardcoded template. Match what the user already does. If two recent notes disagree, prefer the most recent.

## Update workflow

Every update follows the same loop. Do not skip steps.

1. **Resolve today's file path** from the configured pattern and today's date.
2. **Read the file if it exists.** If it does not exist, also read the most recent prior daily note so you know the template. Do not create today's file unless the user explicitly asks or there is a discrete outcome to log.
3. **Locate the target section** by heading (e.g. `## Done Today`, `## TODO`, `## Notes`). Append within that section. Preserve everything else byte-for-byte.
4. **Dedup before adding.** If a bullet referencing the same PR / ticket / outcome is already there, update it in place rather than adding a second. If a TODO is already present, do not re-add it.
5. **Apply PII redaction** (see below) before writing.
6. **Write back with `Edit`,** not `Write`. Single-line or single-section edits only. Never overwrite the whole file.

## Section voice

The user's existing notes are the final authority. As defaults when no clear convention is visible:

- **Done Today** — one bullet per outcome, past tense, links to PRs / tickets inline. Record what changed, not the process. Meaty rationale goes in Notes; here just leave a one-line summary.
- **TODO** — action-shaped, present tense, with enough context for future-you to act without re-reading the session. Include concrete commands / IDs where relevant.
- **Notes** — heading per topic. Structure as applicable: Symptom / Root cause / Fix / Verification / Trade-off / Decision. Dense. Assume future-you is a competent engineer who has forgotten the session.
- **Standup-style sections** (Yesterday / Today / Blockers, or similar) — terse bullets, mirror what's already there.

General style: terse, file:line references where useful, no preamble, no emojis unless the user uses them, no "let me…" filler.

## Hard rules

- **Read first, always.** The user may be editing in parallel. Respect what's there.
- **Append, never replace** a section unless the user explicitly asks.
- **Do not move items between sections** (e.g. Done → TODO) without asking.
- **Do not touch rendered blocks** — dataview, templater, query, mermaid, etc. They are rendered by Obsidian plugins. Leave them alone even if they look empty or wrong.
- **Do not auto-write at every tool call.** Update on session close, on explicit request, or when a discrete outcome lands (PR merged, ticket closed, decision made).
- **Do not create planning / analysis docs alongside the daily log.** The daily log is the artefact.
- **Preserve all required sections even if empty.** If the template has `## Created` with a dataview block, that block stays.

## PII redaction

Daily logs are read by future-you and possibly teammates. Never paste:

- Customer IDs, emails, names
- Order display IDs, account numbers
- API keys, tokens, session IDs
- Internal links that embed any of the above

Replace with `[redacted]` or a one-line summary that conveys the shape of the problem without the identifier. When in doubt, redact.

## Companion behavior

- **"What did I do today?"** — read today's file and summarise from it. Do not regenerate from session memory; the file is the source of truth.
- **"Create yesterday's log"** or any past date — only create if the file does not exist **and** the user is explicit about the date. Never backfill silently.
- **End of session** — offer once: "Want me to update today's log?" Skip the offer if the user has already declined this session or has already updated.

## When something does not fit the template

If the user lands an outcome and no section in the existing template clearly fits, ask before inventing a new heading. Section drift makes future querying (dataview, search) brittle.
