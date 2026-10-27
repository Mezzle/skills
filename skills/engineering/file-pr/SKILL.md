---
name: file-pr
description: File a concise pull request. Use when the user asks to file, open, or create a PR.
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

Open the description with a simple explanation of the problem based on the
user's original prompt, then briefly explain the solution. Do not lead with an
implementation inventory:

BAD

> ❌ Removed implicit workspace carry-over from every "new thread" entry point (cmd+n / cmd+shift+o, sidebar v1/v2 buttons, command palette). New threads inherit only the project from context; branch, worktree, and env mode always come from the configured defaults. Deleted buildContextualThreadOptions, startNewThreadInProjectFromContext, and the v1 sidebar's seed-context machinery.

GOOD

> ✅ My "new worktree" default was ignored when starting new threads on existing worktrees. Super unintuitive. Now your preferences always apply.

Link the ticket the way recent PRs in the repo do. Usually a Jira or Linear key
goes in the title or branch name, and a GitHub issue goes in the body as
`Fixes #123` or `Refs #123`. Take the ticket from the user's request, the branch
name, or the commits. Never invent one. If the repo expects a ticket and you
have none, ask.

End the description with the public model name and harness that made the
changes, for example `Created with <model> in <harness>.` Include subagent
models that wrote part of the change. Use the model name the harness reports.
If model identity is unavailable, name the harness without guessing a model.

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
