---
name: security-review
description: Review security-sensitive changes, triage a vulnerability finding, or validate a security patch in an authorised repository.
---

# Security review

Trace a security concern to evidence and validate the smallest effective fix.
This draft covers code review, finding triage and local patch validation.

## Invocation and configuration

Read `security_review` in the target repo's `.agents/config.yaml` if present.
Explicit requests invoke this skill regardless of `mode`. Workflow hooks use:

- `mode: manual` (default): explicit security-review requests only.
- `mode: auto`: also review changes that alter a trust boundary, or triage a
  substantive security finding. Examples: authentication, authorisation,
  tenant isolation, secret handling, untrusted file parsing, or input reaching
  commands, queries or outbound requests. A filename or dependency update alone
  is insufficient; identify the changed security assumption first.
- `provider`, `model`, `effort`: optional route settings. Explicit user choices
  take precedence. With no model configured, use the current model.
- `access_program: standard | daybreak_blue` (default: `standard`).
- `require_blue: true | false` (default: `false`). True requires
  `access_program: daybreak_blue`; inconsistent settings are a configuration error.

For Blue requests, read [Daybreak access](references/daybreak.md) before
execution. Keep existing general reviewer and council choices intact. If a
different model is configured, use an available authorised delegate route;
give it the scope, base/head, relevant code, checks and requested output below.
In T3, resolve capabilities first and use a fresh `delegate_task` per review
or recheck. If the route is unavailable, report the blocker rather than
substituting another model. Delegates review only and start no subagents.

## Scope

Record the base and current head, working-tree changes, relevant paths, and
whether the task is review, triage or patch validation. Preserve unrelated work.
Use the enclosing workflow's fixed base and finding ledger when supplied.

Identify the assets and systems the user owns or is authorised to analyse.
Repository review and local checks stay within the task's existing permission;
Blue access adds no permission to test deployed or third-party systems.

## Evidence

Read the affected callers, configuration and existing controls. Trace the
attacker-controlled input, required privileges, trust boundary and consequence.
For a bot finding, verify the claimed path before accepting its severity.

Separate suspected issues, source-confirmed issues and locally reproduced
issues. A hypothetical payload alone is not a reproduced vulnerability.
Prefer a safe local fixture or existing test harness for validation. Report
missing context and untested assumptions explicitly.

Each finding needs a stable ID, file:line, prerequisites, impact, evidence,
smallest proposed fix and a focused validation check. Use the enclosing
workflow's severity scale. Otherwise use `blocker` for a demonstrated failure
of the intended security control, `should` for a credible reachable security
bug, and `nit` for optional hardening. Label confidence separately.

## Fix and recheck

Return findings first. Apply fixes only when the enclosing task authorises
editing. Prefer a focused regression check that fails on the vulnerable version
and passes with the fix, plus a check that legitimate behaviour still works.
Record observed results; when reproduction is impractical, explain what source
evidence establishes and what remains unverified.

Use one initial pass and at most two targeted rechecks of material fixes and
open findings. Share the enclosing review-loop's round budget when embedded;
do not create a nested review loop. A changed security assumption invalidates
the affected finding's prior approval. Unresolved material findings or missing
required access prevent a ready verdict; budget exhaustion is not approval.

## Result

Report `clear`, `findings`, or `incomplete`, scoped to the reviewed change.
Include base/head and any uncommitted diff, route/model, observed access status,
findings and dispositions, checks run and limitations. `clear` means no open
material findings in this scope, not a claim that the system is secure.

The parent owns fixes, PR actions and readiness. When embedded, add the result
to its existing ledger and evidence; reuse a result only while it covers the
same code and security assumptions.
