---
name: secrets
description: Use when a task needs a credential, token, API key, password or `.env` value, or before an agent reads, writes, prints, stores or asks for one.
---

# Secrets

Secrets live in a password manager and reach a process at runtime. The
transcript, the repo, memory and delegate briefs only ever hold a
**reference**: a pointer to the vault item, never its value.

## Pick the manager

Read `secrets` in the repo's `.agents/config.yaml`:

```yaml
secrets:
  manager: 1password # 1password | bitwarden
  vault: <optional default vault, collection or project>
```

Without it, use the user's own instructions (for example, a line in their
global `CLAUDE.md` saying which manager covers which kind of work). Still
unknown: ask. One repo, one manager. A secret stays in the manager that owns
it; copy nothing between managers or into another store.

## Read a secret

Every Bash result lands in the transcript. Send the value into a pipe or a
single child process's environment, so the tool result holds only the
command's own output.

**1Password** (`op`). Secret reference: `op://<vault>/<item>/<field>`.

```bash
op run --env-file=op.env -- npm test         # references in the file, values in the child
DB_PASSWORD=op://dev/db/password op run -- ./migrate
op read op://dev/deploy/key | gh secret set DEPLOY_KEY
```

`op run` masks values in its output; `op read` prints raw, so pipe it.

**Bitwarden** (`bw`). Reference: the item ID. Find it without printing the
item: `bw list items --search <name> | jq '.[] | {id, name}'`.

```bash
API_TOKEN="$(bw get password <item-id>)" npm test
bw get password <item-id> | gh secret set API_TOKEN
```

`bw` never masks. Run only commands that leave the value out of their output:
no `printenv`, `env`, `set -x` or debug logging with the variable in scope.
Check the vault state with `bw status | jq -r .status`.

`op item get --reveal`, `op run --no-masking`, `bw get item`, unfiltered
`bw list items` and `cat` on a plaintext secret file all print values. Use the
forms above instead.

## Locked vault or missing CLI

Locked, signed out, or the CLI is absent: stop and tell the user. They unlock
in their own terminal. `op` may show a biometric prompt; that is the user
approving the read.

Shell state does not persist between tool calls, so an exported `BW_SESSION`
is gone by the next call. When the user wants to hand over a session key or a
one-off value, use the harness's secret prompt (T3 Code: `request_secret`,
`delivery: "file"`), then read the file into the child process. Chat is never
the channel for a value. The master password stays with the user: no
`--passwordenv`, no `--passwordfile`.

Lock nothing you did not unlock; the session belongs to the user.

## Write to the vault

Creating, editing or deleting a vault item changes the user's records outside
the repo. Confirm first, with the vault, item name and fields (values omitted).
Let the manager generate new passwords (`op item create --generate-password`).
Any other value travels on stdin from the process that holds it
(`... | op item create -`, `... | bw encode | bw create item --quiet`), so it
never lands in an argument, the process list or a file. Bitwarden writes print
the whole item; keep `--quiet` on `bw create` and `bw edit`.

## Files and the repo

- Commit references: an `op.env` of `op://` paths, or Bitwarden item IDs in
  the script that reads them. Plaintext `.env` stays gitignored, and off disk
  entirely where `op run` can replace it.
- Write no secret into code, tests, fixtures, commit messages, PR bodies,
  comments, logs, memory or screenshots.
- CI reads from its own secret store or a scoped service/machine account
  (1Password service account, Bitwarden Secrets Manager `bws`), not the
  user's personal session.

## Delegates

Pass the manager and reference to a subagent or delegate, never the value.
The delegate reads the secret itself under this skill. Reviewers get the diff,
not the credentials it uses.

## Leaks

A value that reached a tool result, file, commit, PR, log or message is
compromised, even if deleted. Stop, tell the user what leaked and where, and
recommend rotation. Rewriting history or rotating the secret is their call.
