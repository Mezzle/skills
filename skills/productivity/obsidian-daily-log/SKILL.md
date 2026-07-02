---
name: obsidian-daily-log
description: Append outcomes, TODOs, and notes to today's Obsidian daily log, and compile standup-ready day summaries from agent session history, the issue tracker, and meeting notes. Use when the user says "update today's log", "log what I did", "add to my daily note", "summarise yesterday for standup", asks "what did I do today?", or when a discrete piece of work lands and is worth recording. Reads the most recent existing daily note as the canonical template, appends rather than overwrites, dedups, and never touches dataview blocks.
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
4. **Dedup before adding.** If a bullet referencing the same PR / ticket / outcome is already there, update it in place rather than adding a second. If a TODO is already present, do not re-add it — but if new information changes it (a new prerequisite, owner, or deadline), amend the existing bullet in place.
5. **Apply PII redaction** (see below) before writing.
6. **Write back with `Edit`,** not `Write`. Single-line or single-section edits only. Never overwrite the whole file.

## Compiling a day summary (standup mode)

When asked to "review yesterday" or "give me a standup overview", the current conversation is not the source of truth — the day is. Compile from every source available, then write one entry:

- **Agent session transcripts** (e.g. `~/.claude/projects/*/*.jsonl` for Claude Code). Two traps:
  - **Sweep all project directories, not just the current one.** A day's work is usually spread across several repos, each with its own transcript directory.
  - **Filter by entry timestamp, not file mtime or session start.** Sessions survive multiple days: a session started last week can contain yesterday's work, and yesterday's session can contain this morning's. Select transcript entries whose timestamps fall inside the target day.
  - Extraction technique: user messages give the tasks; the last substantial assistant messages per topic give the outcomes. Never load whole transcripts — script the extraction and truncate aggressively.
- **Issue tracker** (CLI or MCP — `jira`, `gh`, `linear`, etc.): issues updated in the window, status transitions, PRs raised. Careful: "updated in window" ≠ "worked on" and ≠ "created" — verify with a creation-date query before writing "raised N tickets".
- **Meeting notes tool** (e.g. a meeting-notes MCP such as Granola): list meetings in the range and pull summaries. If no such tool is connected, do not scrape the app's local data store — these are commonly encrypted; tell the user what's missing and offer to connect the tool instead.
- **The previous day's daily note**: checked-off TODOs are outcomes; unchecked ones are context.
- **Vault files created/modified that day** — often the artefacts the summary should link to.

Writing the entry:

- One parent bullet per compilation (e.g. `**Standup — yesterday** (compiled from sessions + issue tracker):`) with nested bullets, one per workstream. Name the sources — future-you should know the provenance.
- Each workstream bullet: bold lead keyword, then outcome-first prose with PR/ticket/commit refs inline and `[[wikilinks]]` to any vault notes created that day.
- Scale of evidence matters more than polish: a missed workstream is a worse failure than a wordy bullet.

## Meeting actions → TODOs

When a meeting summary contains action items, **capture every uncaptured TODO**:

- Any action assigned to the user that is not already in the TODO section gets added — this is not optional; a lost standup commitment is the costliest miss this skill can make.
- Actions assigned to other people are context, not TODOs — mention them in the log entry if relevant, don't add them to the user's list.
- If an action relates to an existing TODO, amend that bullet in place (add the prerequisite / constraint / deadline) rather than adding a near-duplicate.
- If an action was already completed by other work that day, record it as done in the log entry and note which standup action it closes, instead of adding a TODO.

## Section voice

The user's existing notes are the final authority. As defaults when no clear convention is visible:

- **Done Today** — one bullet per outcome, past tense, links to PRs / tickets inline. Record what changed, not the process. Meaty rationale goes in Notes; here just leave a one-line summary.
- **TODO** — action-shaped, present tense, with enough context for future-you to act without re-reading the session. Include concrete commands / IDs where relevant.
- **Notes** — heading per topic. Structure as applicable: Symptom / Root cause / Fix / Verification / Trade-off / Decision. Dense. Assume future-you is a competent engineer who has forgotten the session.
- **Standup-style sections** (Yesterday / Today / Blockers, or similar) — terse bullets, mirror what's already there.

General style: terse, file:line references where useful, no preamble, no emojis unless the user uses them, no "let me…" filler.

## Hard rules

- **Read first, always.** The user may be editing in parallel. Respect what's there.
- **User edits are feedback.** If the user deleted or reworded something you added earlier, never re-add or "fix" it — a deletion is a redaction decision. Treat the deleted item's category as sensitive for the rest of the session.
- **Append, never replace** a section unless the user explicitly asks. (Replacing an entry you yourself wrote earlier in the same session, to extend or correct it, is fine — but only the parts you wrote.)
- **Do not move items between sections** (e.g. Done → TODO) without asking.
- **Do not touch rendered blocks** — dataview, templater, query, mermaid, etc. They are rendered by Obsidian plugins. Leave them alone even if they look empty or wrong.
- **Do not auto-write at every tool call.** Update on session close, on explicit request, or when a discrete outcome lands (PR merged, ticket closed, decision made).
- **Do not create planning / analysis docs alongside the daily log.** The daily log is the artefact.
- **Preserve all required sections even if empty.** If the template has `## Created` with a dataview block, that block stays.

## PII and sensitivity redaction

Daily logs are read by future-you and possibly teammates. Never paste:

- Customer IDs, emails, names
- Order display IDs, account numbers
- API keys, tokens, session IDs
- Internal links that embed any of the above

Replace with `[redacted]` or a one-line summary that conveys the shape of the problem without the identifier. When in doubt, redact.

Beyond hard PII, some internal topics are sensitive in a log others may read — security incidents, credential exposures, HR/people matters. Colleague first names in ordinary work context are usually fine (follow the note's existing convention), but keep incident detail vague by default, and follow the user's lead: if they trim such an item, that category stays out.

## Companion behavior

- **"What did I do today?"** — read today's file and summarise from it. Do not regenerate from session memory; the file is the source of truth.
- **"Create yesterday's log"** or any past date — only create if the file does not exist **and** the user is explicit about the date. Never backfill silently.
- **End of session** — offer once: "Want me to update today's log?" Skip the offer if the user has already declined this session or has already updated.

## When something does not fit the template

If the user lands an outcome and no section in the existing template clearly fits, ask before inventing a new heading. Section drift makes future querying (dataview, search) brittle.
