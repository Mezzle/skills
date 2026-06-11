# Why each rule exists — the case study

Each rule in SKILL.md was paid for. This file records the failure that minted it,
so the rules read as evidence rather than dogma.

## The case in one paragraph

A Next.js 16 standalone storefront OOM-recycled on a clock in prod. A dev's first
read was "we're just filling an in-memory cache" (benign). Investigation showed a
real, time-proportional heap leak driven by an uptime monitor hitting `/search`
every 60s. After ruling out Sentry (twice), a Redis write-speed theory (shipped,
A/B'd, refuted, reverted), and a Next version bump, the cause was the
storefront's own cache handler: an unevicted per-request `#requestCache` Map
parking every cached response body. One session also concluded — wrongly — that
Next itself retained the per-request `IncrementalCache` via its RSC
`flightResponses` WeakMap, and handed that to a second session as fact. The
second session refuted it: the retainer trace had walked weak edges as strong.

## Rule-by-rule

### 1. Toggle, don't theorise
Sentry was "identified" as the cause twice from code reading and changelog
correlation (scope/context issue #18220, then HTTP instrumentation). Both
collapsed the moment the integrations were actually stripped and the load
re-run: leak unchanged. Conversely, a `trackTags` pipelining "fix" was shipped on
a plausible mechanism (slow Redis writes holding requests open) and refuted by
its own A/B (+130 MB, envelopes still present). Reading finds candidates; only
removal under identical load finds causes.

### 2. Time-proportional vs request-proportional
Prod slope barely moved across a 3.6× traffic difference and was flat at idle —
time-driven. Later, a real retention mechanism was found (blocked Sentry egress
pinning request graphs via never-settling `waitUntil` promises), but it scaled
with concurrent requests (174→318 under load, draining at idle). The
proportionality mismatch alone disqualified it as the prod driver, no further
experiments needed. Classify first; it prunes the tree.

### 3. Positive control
The clean-room repro showed *no* growth. Before trusting that, a deliberate leak
(module-level array accumulating each request's payload) drove heapUsed
20→488 MB on the same rig. Only then did "flat" mean "no leak" rather than
"blind harness".

### 4. Metric = symptom, not hypothesis
The first upstream-session runs counted `IncrementalCache` *instances* because
the handed-off theory named that class. The counts were noisy and non-monotonic
(42→6→63) — they tracked open sockets. Switching to per-type heap pools (the
actual prod symptom: string/object/array growth) is what surfaced the real
accumulators (Sentry `_sentSpans` LRU, PostHog flag-call map) and their bounds.

### 5. Timescale
3-minute bursts showed JIT `code`-pool warmup and nothing else. The bounded
accumulators only became visible (and provably bounded — LRU cap at 10k, reset
at 50k) over 20-minute runs with interval snapshots at 0/7/14/20 min.

### 6. The GC invariant and weak edges
`v8.writeHeapSnapshot()` and the SIGUSR2 trigger force a full GC before
capture. Therefore everything in a snapshot is strongly retained — GC already
tried to collect it and failed. A reverse-BFS retainer walk that treats
`edge.type === 'weak'` like a strong edge will route through module-level
WeakMaps (which are permanently GC-root-reachable) and "bottom out" there,
producing a plausible, specific, *wrong* retainer. That exact artifact —
"retained via a Promise in the `flightResponses` WeakMap" — survived a session
handoff and nearly became an upstream Next.js bug report. The corrected walk
landed on a live keep-alive TCP socket: bounded, benign, expected.

**Also expect and discount:** the socket-bounded chain (libuv handle → TCP →
IncomingMessage → request meta → per-request objects). It looks like retention,
scales with open sockets, and drains on idle.

### 7. Faithfulness gaps
The fix (removing `#requestCache`) could not be validated locally: prod commerce-API
payloads are large and numerous; local dev payloads were ~0.01 MB, so the
envelope pile physically couldn't accumulate. The honest move was to state the
gap, ship on the strength of the mechanism + partial local evidence, and
designate prod observation as the confirmation step. It confirmed: pre-fix
cycles ramped linearly to ~95% over 5–7h; post-fix plateaued at ~20–25%.

### 8. Handoff confidence-labelling
The handoff brief listed the WeakMap retainer under "What is already settled (do
not re-test)". It was an unvalidated trace from buggy tooling, but nothing in
the document distinguished it from the A/B-proven items beside it. The receiving
session burned its opening steps building on it before the refutation. Label
claims: `A/B-proven` / `traced-but-unvalidated` / `inferred`.

## Prod-confirmation craft

- Judge **shape at equal task age**, not absolute level: plateau vs linear ramp.
- Wait out the historical time-to-ceiling before declaring victory.
- Keep the observation window clean: an attached Chrome inspector pins heap
  roots, suppresses GC, and each DevTools snapshot allocates a large transient
  buffer. In this incident a colleague's attached debugger (plus an accidental task
  kill) contaminated the first two post-deploy hours; only the window after
  detach was usable evidence.
- Bounded ≠ broken: LRU plateaus and reset-sawtooths (Sentry `_sentSpans` cap
  10k; PostHog `distinctIdHasSentFlagCalls` reset at 50k — large amplitude under
  cookieless bot traffic) are hygiene items, not OOM drivers. Note them,
  don't chase them.
