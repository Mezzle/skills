---
name: own-the-baseline
description: >-
  Run when you're about to call an error, warning, or failing check "pre-existing," "unrelated," or "out of scope" in a codebase you've contributed to — or when verifying a change with lint/typecheck/test/build. Treat every red result as ours: fix it, or surface it for an explicit decision. Never let "pre-existing" be a reason to leave it.
---

# Own the Baseline

In a codebase you've worked on, there are no "pre-existing" errors. If it's broken, we broke it — past us, present us, doesn't matter. "Pre-existing" is not a category that excuses leaving a check red.

## The thesis (lead with this)

"Pre-existing" and "out of scope" are the two phrases that quietly let a broken baseline rot. They feel responsible — *I'm staying focused on my task* — but in a project you co-own they're a way of disclaiming code you're responsible for. Catch yourself reaching for them. The reflex should be the opposite: a red check you just ran is **yours to resolve**, even if you didn't type the line that broke it.

## The rule

When `lint` / `typecheck` / `test` / `build` comes back red:

1. **Don't filter it out.** Resist "those errors were already there." You ran the command; the output is now your responsibility.
2. **Default to fixing.** Most "pre-existing" lint/type errors are small and were introduced by us. Fix them in the same change. A green baseline is the deliverable, not just the feature.
3. **If you can't or shouldn't fix it inline, surface it loudly** — name each failure, say why it's out of scope *this time*, and get an explicit decision. Never silently skip and never bury it under a `tail` that hides the count.
4. **Re-run until green** (or until the human has explicitly accepted specific reds). "Lint passes except for some old stuff" is not passing.

## Fixes, not suppressions

Prefer the fix that removes the cause over the one that hides it:

- A directive that suppresses nothing is a tell. `@ts-ignore` silently no-ops when the line has no error — switching to `@ts-expect-error` exposes those (TS `error TS2578: Unused '@ts-expect-error' directive`). Delete the dead directive rather than keeping a lie.
- A rule firing across *every* file of a kind (e.g. `react-refresh/only-export-components` on every React Router route that exports `meta`/`loader`) is usually **misconfigured for the framework**, not N code smells. Fix the config (`allowExportNames`, `argsIgnorePattern: '^_'`), don't mutilate idiomatic code or sprinkle inline disables.
- Empty `catch {}` → add a one-line reason, don't disable `no-empty`.
- Underscore-prefixed unused params are a signaled intent — teach the linter (`argsIgnorePattern: '^_'`), don't rename or delete framework-required params.

## When it genuinely isn't yours

Vendored code, generated output, a third-party dir, or a separate team's package you've never touched — that's a real boundary. Even then: don't *silently* skip. State "X is vendored/generated, leaving it" so the skip is a visible decision, not an omission. The bar is **explicit**, not **avoided**.

## Anti-patterns

- "These errors are pre-existing and unrelated to my change." → They're in a repo you ship. Fix or surface.
- `pnpm lint 2>&1 | tail -20` hiding that there were 25 problems across 12 files. → Read the whole count before deciding anything.
- Marking your own task done while a check is red "but it was red before too."
