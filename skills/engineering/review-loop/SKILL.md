---
name: review-loop
description: Use when the user says "review loop" or "sol loop".
---

# review-loop

This is a workflow for making your code changes more correct before (or
sometimes after) filing a pull request. tl;dr - have a model from another
provider review your code in a loop.

Make the most minimal possible changes to appease the reviewer. Be careful
of scope creep and don't be scared to push back.

## Reviewer

Pick the reviewer in this order:

1. A model the user names in the request. "sol loop" names GPT Sol.
2. The `reviewer` entry in `.agents/config.yaml` at the repo root: a
   `provider` (the route, as the harness names it), a `model`, and an
   optional `effort`. A model family such as `GPT Sol` means the latest model
   in that family. An exact ID pins it.
3. The latest GPT Sol.

Do not hardcode an ID. Do not substitute a model the user or the config
named. If no route runs it, report the blocker.

## Budget

- Default: 3 rounds total. Round 1 is full. Later rounds check only
  changed code and open findings.
- Extend to 5 only for security, permissions, auth, data loss, or
  state/concurrency, while a blocker or should stays open with evidence. Or when
  the user asks.
- Stop early if a round returns only nits. Declined nits and comment,
  doc, or format-only fixes need no new round.
- One general reviewer only. An enabled security pass below may use its
  configured route sequentially. All review passes share this round budget;
  reviewers must not start subagents or reviewers.
- Keep a ledger: id, severity, outcome, usage if returned. Never guess it.

## 1. Scope

Run `git status --short`. Do not stash, discard, or include unrelated
changes. Limit review to the change paths if they separate cleanly.
Otherwise stop and ask.

Find the base after `git fetch origin`:

- PR: `gh pr view <n> --json baseRefName,headRefOid`. Check out the branch
  only if clean. Confirm `HEAD` is the PR head, or ahead only by this
  change. Base: `git merge-base HEAD origin/<baseRefName>`.
- Local: `git merge-base HEAD origin/<default-branch>`. No remote: a base
  the user names, or `HEAD` for uncommitted changes only.

The change is base to working tree in those paths, with untracked files.
Use one diff command all rounds. State intent and out-of-scope in 1-2
sentences. Run covering checks. Do not send code this change breaks. Note
missing or pre-failing checks in the brief.

### Spec and standards

Find the spec, first match wins: issue refs in the change's commit messages
(fetch through `tracker` in `.agents/config.yaml`), a path the user gave, a
file under `docs/`, `specs/` or `.scratch/` matching the branch or feature.
None found: `Spec: none`, and the reviewer checks against intent.

List the standards sources: every file that documents how code is written
here, including `CODING_STANDARDS.md`, `CONTRIBUTING.md`, `AGENTS.md` and
`CLAUDE.md` when they exist. None found: `Standards: none`.

### Optional security pass

Read `security_review` in `.agents/config.yaml`. For an explicit security
review request, or `mode: auto` when the change alters a trust boundary,
load the available `security-review` skill. In this source checkout its draft
is [here](../../in-progress/security-review/SKILL.md); copied installations
need that skill installed separately. If it is needed but unavailable, report
an incomplete security review rather than silently skipping it.

Run the security pass before general review, sharing the fixed base, scope,
ledger and round budget. Preserve the general reviewer selected above. If it
also satisfies the security route settings, combine both briefs in one pass;
otherwise run the passes sequentially. Include security findings in the
general review brief and recheck material security fixes within the remaining
budget. Readiness requires both reviews to cover the current behaviour, with
no open material findings or incomplete required security review. An absent
configuration leaves this workflow unchanged unless explicitly requested.

## 2. Start the reviewer

In T3, call `orchestrator_capabilities` and resolve the reviewer. Record
provider, model, and effort only if exposed. Use `delegate_task` every round
(`role: "review"`, `mode: "async"`). Save `taskId`. New `clientRequestId` per
round. `childThreadId` is storage, not the next target. Do not use
`t3_thread_send`, `create_threads`, or `t3_thread_launch` for review.

If T3 tools are not listed, try one direct capability call. Outside T3, use
a native subagent that runs the reviewer model and keep its ID. In Claude
Code, use a custom subagent only if it is set up to run that model.

Do not edit scoped files while review runs. Wait for the notice. Do not
poll or start a second reviewer. Timeout, error, or no reply is not
approval. On failure, cancel, verify stop, restart with the ledger.

Round 1 brief (T3 children get no history):

```
Review only. Do not edit, commit, push, comment on PRs, or start subagents.
Repo: <abs path> Base: <sha> Intent: <intent> Out of scope: <scope> Checks: <results>
Spec: <issue, path, or none> Standards: <files, or none>
See: git diff <base> [-- <paths>]; git status --short (read untracked).
Read surrounding code, the spec and the standards. Check:
- Bugs: wrong behaviour, broken callers.
- Spec: requirements missing, partial or implemented wrong. Quote the spec
  line. Spec none: check against intent.
- Standards: breaches of a documented standard (cite file and rule). Also
  these smells, each a judgement call labelled "possible <smell>": Mysterious
  Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession,
  Repeated Switches, Shotgun Surgery, Divergent Change, Speculative
  Generality, Message Chains, Middle Man, Refused Bequest. A documented
  standard overrides a smell. Skip what tooling enforces.
Hold to the smallest change. Flag code, tests, guards or abstractions the
intent does not need: scope creep. Other paths, rare cases, small perf,
extra compat: nits.
blocker = intended case wrong, or a spec requirement missing or wrong.
should = real bug callers will hit, in intent, or a documented-standard breach.
nit = smells, scope creep, the rest.
Only nits: APPROVE, unless there are a lot of them.
Reply:
VERDICT: APPROVE or CHANGES
S1 [blocker|should|nit] <file>:<line> <claim>. Fix: <suggestion> (stable ids)
```

## 3. Answer findings

Check each finding and severity yourself. Another path, rare case, or
small cost is a nit, whatever label it came with.

- Agree: smallest fix. Prefer delete or narrow over new lock, cache,
  helper, or option. Fix the case that happened. Add one focused test
  that fails without the fix, if intent needs it.
- Disagree: say why, with evidence (file:line, test, output).
- Out of scope or nit: decline in one line. List as follow-up.
- Smell: take the fix only if it shrinks the diff.

Update the ledger. Re-run checks and `git diff --shortstat <base>`. If
review grew the diff, cut first. Do not agree just to end the loop.

## 4. Next round

Start one only if budget remains and a blocker or should is open, behaviour code
changed, or approval does not cover the current behaviour diff. Use a fresh
`delegate_task` in T3, or follow up the saved native ID. Send the round 1 brief,
the ledger (`fixed:` / `disagree:` / `declined:` + evidence), the same base
diff, and the change since last round. Tell the reviewer: open ids and changed
code only. Mark each old id `resolved` or `still open: <reason>`.

## 5. Stop and ship

Agreed: APPROVE on the current behaviour diff, no blocker or should open,
no concern of your own. Stuck: an item stays disputed after two replies,
or budget ends. Show both sides in 2-3 lines each. The user decides.
Budget end is not approval.

Do not push during the loop. Push after agreement only if the user asked
to push, ship, or update the PR. If you push to a PR, add above the model
blurb:

`Reviewed with review-loop: <N> rounds with <model>. Verdict: approved`.

Add `on <effort>` only if verified.

Report: rounds, model, what the reviewer changed, diff size before/after,
fixed and declined findings with reasons, usage if exposed (else say not),
pushed or not.
