---
name: file-pr
description: File a concise pull request, or rewrite an open one's description. Use when the user asks to file, open, or create a PR, or when another skill files or updates one.
---

# File PR

## Repo settings

Read `.agents/config.yaml` at the repo root if it exists. Two keys apply here:

- `tracker`: where this repo's work is ticketed: `jira`, `github`, `linear`, or
  `none`.
- `review_bots.request`: bots to request a review from once the PR is open.

Without `tracker`, infer it from recently merged PR titles, branch names, and
bodies: Jira and Linear keys look like `ABC-123`, GitHub issues like `#123`.
If none show up, the repo does not use one.

## Filing

Before filing, check whether a PR for this branch already exists. Review the
diff locally against the base branch (usually `origin/main`) to make sure its
contents match the goal.

PR titles usually become commit messages, so follow the repository's title
conventions. Look at recently merged PRs and Git history for examples. Prefer a
concise, human-readable title that explains why the change matters:

BAD

> ❌ perf(server): negotiate permessage-deflate on the websocket

GOOD

> ✅ perf(server): cut websocket frame size by 70%+ with gzipping

## Description

Use this shape, in this order. Skills that add their own section (council,
review-loop) put it after Merge Danger and before the closing model line.

```markdown
## Summary

<the problem, then the fix, in a sentence or two>

<one visual>

## Evidence

- **Before:** <failing test, error output, screenshot>
  **After:** <the same thing passing>
- **Not verified:** <what you could not prove>

## Merge Danger

**Door:** <one-way or two-way>, <why>
**Blast Radius:** <what could break, and for whom>

<ticket link, extra sections>

Created with <model> in <harness>.
```

Keep prose short and use the repo's own terms (its glossary or `CONTEXT.md` if
it has one).

### Summary

Open with a simple explanation of the problem based on the user's original
prompt, then briefly explain the solution. Do not lead with an implementation
inventory:

BAD

> ❌ Removed implicit workspace carry-over from every "new thread" entry point (cmd+n / cmd+shift+o, sidebar v1/v2 buttons, command palette). New threads inherit only the project from context; branch, worktree, and env mode always come from the configured defaults. Deleted buildContextualThreadOptions, startNewThreadInProjectFromContext, and the v1 sidebar's seed-context machinery.

GOOD

> ✅ My "new worktree" default was ignored when starting new threads on existing worktrees. Super unintuitive. Now your preferences always apply.

Under it, add the smallest visual that makes the change clear:

- **Pseudocode** for logic or an algorithm.
- **Call tree** for runtime control flow.
- **Component tree** for UI structure, with the state and module boundaries that
  matter.
- **File tree** for file responsibilities or a broad refactor.
- **Mermaid** sequence or flow diagram for interaction or data flow between
  parts.
- **`diff` of any of the above** when the shape already exists and the point is
  what changes:

```diff
 submitForm
   createSession
     persistPrompt
+    expandSkillMention
     launchAgent
```

Show only the calls, files, props and states the reader needs. One visual is
usual and two is plenty. Skip it for a one-line fix.

### Evidence

Put the proof here: what you observed yourself, shown as before and after.
Screenshots are best for a visual change. Test runs and command output come
next. Name the test that failed without the change and passes with it. For a
new feature the "before" is that test, or a synth or build, failing or lacking
the new output. Always list what you could not verify.

If a security review ran, include its scope/head, material finding dispositions,
patch-validation evidence and limitations here. Name Daybreak Blue only when
the review verified its use; otherwise state standard or unverified access.
Reuse the review result rather than launching another pass to file the PR.

### Merge Danger

A two-way door can be rolled back cheaply. A one-way door cannot: data
migrations, deletions, published APIs, anything users start depending on.
Say which, and when a two-way door turns one-way. The blast radius is who or
what breaks if it goes wrong: consumers, environments, layout, mobile.

### Ticket and attribution

Link the ticket the way recent PRs in the repo do. Usually a Jira or Linear key
goes in the title or branch name, and a GitHub issue goes in the body as
`Fixes #123` or `Refs #123`. Take the ticket from the user's request, the branch
name, or the commits. Never invent one. If the repo expects a ticket and you
have none, ask.

End the description with the public model name and harness that made the
changes, for example `Created with <model> in <harness>.` Include subagent
models that wrote part of the change. Use the model name the harness reports.
If model identity is unavailable, name the harness without guessing a model.

### Updating an open PR

When a later push changes behaviour or the diff's shape (a review fix, a
rebase, a takeover), edit the body with `gh pr edit <pr> --body-file <file>` so
Summary and Evidence describe the current head. Keep the other sections.

## Opening the PR

Before submission, check the title, description, quotes, and attachments for
secrets and private details.

Open a real PR rather than a draft so review bots run. If `gh pr create` fails
because the GraphQL rate limit is used up, open it through REST with
`gh api repos/<owner>/<repo>/pulls -f title=... -f head=... -f base=... -F body=@<file>`.

Once the PR is open, request a review from each bot in `review_bots.request`,
for example `gh pr edit <pr> --add-reviewer @copilot`. If the user also asked
to babysit it, continue with the `babysit-pr` skill.

Do not post a follow-up PR comment unless it serves the user's request. When a
comment is needed, use the `leaving-pr-comments` skill.
