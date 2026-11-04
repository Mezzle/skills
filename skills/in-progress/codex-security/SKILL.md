---
name: codex-security
description: Run when the user explicitly asks for "Codex Security" (codex-security, cs) to scan a change, triage a security finding, or verify a security fix.
---

# Codex Security

Scan with the Codex Security CLI (`codex-security`, alias `cs`) and report
findings verified against source. Use only when the user names Codex Security;
other security review stays with `security-review`.

## Preflight

Run `codex-security --version` and `codex-security login status`. If either
fails, return `incomplete` with the error. The user asked for this scanner, so
review on no other model in its place.

Take `--model`, `--effort` and provider from the user's request; otherwise use
the CLI defaults. Provider is `--provider` on `scan` and
`--codex model_provider="<provider>"` elsewhere. A rejected setting is
`incomplete`.

## Scope

Record the base and current head, working-tree changes, and whether the task
is review, triage or patch validation. Use the enclosing workflow's fixed base
and finding ledger when supplied.

## Commands

Run from the repository root:

| Task | Command |
|---|---|
| Review | `scan . --diff <base> --head <head> --headless --json --show-cost` |
| Uncommitted changes | `scan . --working-tree --base HEAD --headless --json --show-cost`, as a separate run |
| Triage | `validate <finding text or file>` (text output only) |
| Patch validation | `verify-fix <finding text, file or saved ID> --json` |

Use only these and the read-only `scans show`, `scans logs` and `findings
list`. Leave results in the CLI's state directory, outside the checkout. Pass
`--max-cost` only when the user sets one; it caps the API-price estimate, not
ChatGPT allowance. `codex-security <command> --help` is the flag reference.

For Daybreak Blue, only when asked: `scan --cyber-access-program daybreak_blue`,
and `--codex daybreak=true` on `validate` and `verify-fix`. An accepted flag
does not prove Blue is active; report access as `unverified` unless the output
shows the effective programme.

## Findings

Scanner findings are candidates. For each, read the affected code and trace
the attacker-controlled input, trust boundary and consequence. Keep its
`findingId` as the stable ID. Grade from that evidence, not the CLI's level:
`blocker` for a demonstrated failure of the intended security control,
`should` for a credible reachable security bug, `nit` for optional hardening,
unless the enclosing workflow has its own scale.

Scope findings to this change. The scan's `findings` are in scope.
`repositoryFindings` spans every scan of the repository: carry forward only
IDs already in the enclosing ledger, or with no ledger, those whose `targetId`
matches this scan's target. A carried finding stays open until `verify-fix` or
source evidence shows it fixed, whether or not the latest scan reconfirmed it.

Discovery varies between runs, so a scan with no findings is not `clear`
without your own pass over the changed trust boundaries. A `status: failed`
result is `incomplete`.

## Result

Report `clear`, `findings`, or `incomplete`, scoped to the reviewed change.
Include base/head, scan IDs, model, cost, access status, findings with
file:line and dispositions, and limitations. Return findings only; the parent
or user owns fixes and PR actions.
