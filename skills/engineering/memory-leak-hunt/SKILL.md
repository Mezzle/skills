---
name: memory-leak-hunt
description: Disciplined investigation of Node.js / Next.js production memory leaks using heap snapshots, A/B toggles, and weak-edge-correct retainer analysis. Use when a service shows growing RSS/heapUsed, OOM recycles, memory-target autoscaling churn, or someone suspects "a cache filling up" — before accepting any hypothesis about the cause.
---

# Memory leak hunt

Methodology distilled from a real production incident (a Next.js 16 standalone
ecommerce storefront with a custom Redis cache handler) where a
confident-but-wrong retainer theory survived a session handoff because of a
heap-tooling bug. The case study and the deeper "why" behind each rule:
[METHODOLOGY.md](METHODOLOGY.md).

## The iron rules

1. **Toggle, don't theorise.** A hypothesis is settled only by an A/B: remove or
   neuter the suspect, re-run the same load, compare. Code reading produces
   *candidates*, never verdicts. Every wrong call in the case study was asserted from
   reading; every right one came from a toggle.
2. **Classify the growth first: time-proportional vs request-proportional.**
   Plot memory vs wall-clock at different traffic levels. Slope ~constant across
   traffic ⇒ time-driven (cron, monitor, TTL/revalidate cycle). Slope scales with
   traffic ⇒ request-driven. This single discriminator kills whole hypothesis
   families (it ruled out a Sentry-egress mechanism that only pinned memory
   per-request).
3. **Run a positive control before trusting any negative result.** Deliberately
   inject a leak (push each request's payload into a never-cleared module array)
   and confirm the rig shows it. A flat graph from an unproven harness is noise.
4. **Match the metric to the symptom, not the hypothesis.** Diff per-type heap
   pools (string/object/array totals) between snapshots; don't count instances of
   the class you suspect — a wrong suspicion hides the signal.
5. **Match the timescale to the symptom.** A leak that takes hours to bite needs
   ≥20-min runs with interval snapshots. Short bursts measure JIT warmup.
6. **Know the GC invariant.** Snapshot capture forces a full GC, so everything in
   a snapshot is *strongly* retained. "Retained via a WeakMap value" is therefore
   impossible — if a retainer trace bottoms out at a WeakMap, the *tooling* walks
   weak edges as strong. Use `scripts/analyze.mjs` (weak-edge-correct).
7. **State what your repro cannot exercise.** If prod payloads are large and local
   ones tiny, a local A/B can't prove a payload-proportional fix — say so and
   designate prod observation as the confirmation step instead of forcing it.
8. **Hand off confidence levels, not just conclusions.** Label every claim
   `A/B-proven` / `traced-but-unvalidated` / `inferred`. An unlabelled inference
   reads as fact downstream and costs the next session real effort to undo.

## Workflow

1. **Characterise** — memory graphs over ≥24h: shape (sawtooth-to-ceiling?),
   what's hitting the box on a clock (uptime monitors, cron), staging-vs-prod
   delta, deploy markers. Check `process.memoryUsage()`: heapUsed vs external vs
   arrayBuffers point at different suspect classes.
2. **Reproduce** — standalone build + realistic backing services; drive with the
   *prod access pattern* (`scripts/drive-noka.mjs` for low-concurrency
   `Connection: close` monitors). Snapshot via `--heapsnapshot-signal=SIGUSR2`
   (GCs before write) or an `--expose-gc` + `v8.writeHeapSnapshot()` route.
3. **Validate the rig** — positive control (rule 3). Then baseline + interval +
   final snapshots over ≥20 min.
4. **Diff** — `scripts/summary.mjs` (pools), `scripts/diff2.mjs` (per-constructor
   delta), `scripts/count-leaks.mjs` (top growers). Distinguish *bounded* piles
   (LRUs, sawtooth dedup maps — note their caps) from unbounded ones.
5. **Trace** — `scripts/analyze.mjs <snap> <Constructor>` for the strong retainer
   chain to a GC root. Distrust chains through WeakMaps (rule 6); expect benign
   socket-bounded retention (live keep-alive socket → IncomingMessage →
   request meta) and don't mistake it for a leak — it drains on idle.
6. **Fix & A/B** — smallest toggle that removes the retainer; re-run the exact
   same load; the leaking constructor must *vanish from the top growers*, not
   just shrink.
7. **Confirm in prod** — deploy, then judge the *shape* at equal task age vs
   pre-fix cycles (plateau vs linear ramp). Wait out the old time-to-ceiling
   before stamping "confirmed". Nobody attaches a debugger to the task while
   you're measuring — an attached inspector pins heap roots and its snapshots
   spike memory, contaminating the window.

## Scripts

Node ESM, no deps; run against `.heapsnapshot` files. `analyze.mjs` (instance
counts + weak-edge-correct retainer BFS), `diff2.mjs`, `summary.mjs`,
`count-leaks.mjs`, `drive-noka.mjs` (sequential no-keep-alive load driver).
