---
name: chestertons-fence
description: >-
  Run before removing or rewriting existing code you can't explain, and when making a choice the next reader would question.
---

# Chesterton's Fence

Every session starts cold: you are always the developer reading this code six months later. The code says _what_; the _why_ lives in history, tests and docs, or nowhere. Treat odd code as a **fence**: someone put it there for a reason until you've shown otherwise.

## Before removing a fence

Applies to a guard, retry, special case, sleep, duplicated check, unusual ordering or workaround whose purpose you can't explain and are about to delete or rewrite, including as a side effect of a refactor.

1. **Dig.** Run `git log -L <start>,<end>:<file>` (or `git blame` then `git show <sha>`) on the lines. Read the commit message and the linked PR or issue.
2. **Check the record.** Search ADRs, `CONTEXT.md` / glossary and why-comments near the code for the behaviour.
3. **Check the tests.** Find tests that exercise it; run them after your change.
4. **Decide**, and quote the evidence in your reply:
   - Reason found and still live: keep the fence. If it now looks redundant, say so and leave it.
   - Reason found and gone (the upstream bug fixed, the constraint lifted): remove it, and cite the reason it's gone in the commit message.
   - No reason found: surface it to the user with what you checked and ask. Leave the fence standing meanwhile.

Done when every fence you touched has one of those three verdicts with evidence.

## Building a fence

When you make a choice the next cold reader would question (a workaround, an ordering dependency, a rejected obvious approach, a magic value), label it where they'll look:

- **Local reason** → a one-line why-comment beside the code ("upstream returns 502 on cold start; retry once").
- **Reason for the change** → the commit message body.
- **Architectural decision** → an ADR (see `domain-modeling` if installed).

Then ask whether a check could carry the lesson instead: a test, type, lint rule or hook. A check can't go stale silently; prefer it to prose, and keep the prose for the why.

