---
name: managing-llm-configs
description: Use this skill to put an LLM call under remote control — model, parameters, and prompt managed as targetable runtime config via LaunchDarkly AI Configs behind an OpenFeature flag, with PostHog observability and safe in-code fallbacks. Use when feature-flagging or remotely managing an LLM call, especially on Cloudflare Workers/edge where the naive setup silently breaks.
---

# Managing LLM Configs

Put an LLM call under **remote, targetable config control** — model id, parameters, and prompt served as versioned runtime config — with observability and safe fallbacks. Opinionated integration recipe, not a framework.

## The thesis (lead with this)

This is **not** on/off feature flagging. On/off is the degenerate case. The capability is serving a **bundle** — model id, model parameters, and prompt — as **targetable, versioned runtime config** that can vary by user segment, rollout %, or experiment.

The architectural move: **the model/prompt/params leave the deploy artifact and become runtime config.** A reader who thinks "feature flag = boolean" will badly under-use this. Adopting it as your *primary* prompt-handling path is a deliberate commitment — see trade-offs.

## Retrieval-first

SDK names and APIs move fast. Before writing wiring code, fetch current docs (the `ctx7` CLI / `find-docs` skill) for: LD Cloudflare edge SDK, `@launchdarkly/server-sdk-ai`, `@openfeature/server-sdk`, Vercel `ai` + `workers-ai-provider`, PostHog. Do not trust memorized signatures. Versions verified at authoring time are noted inline as a starting point, not gospel.

## Two LaunchDarkly products, wired together (don't conflate them)

LD exposes these as separate UI areas, reached by **different SDKs**:

| LD area | Holds | Accessed via |
|---|---|---|
| **Features → Flags** | the on/off gate (e.g. `ld-ai-moderation`) | OpenFeature (`@openfeature/server-sdk`) + provider |
| **Agents → Configs** (AI Configs) | the model + prompt + params bundle | the AI SDK (`@launchdarkly/server-sdk-ai`) — **not** OpenFeature |

The flag gates *whether* you consult the AI Config; the AI Config supplies *what* to run. OpenFeature wraps only the flag (so the flag vendor stays swappable); the AI Config stays LD-direct (no vendor-neutral equivalent exists, and it's meant to be reversible).

## Make the decision explicitly

State this in any project that adopts the pattern: **"Is LD your canonical prompt store, or a runtime override over an in-code default?"** The answer drives governance and testing. Trade-offs if LD becomes canonical:

- **Source of truth leaves git.** Editing prompts without a deploy is the upside; the cost is prompt changes bypass code review/PR. LD has change history + approvals, but that's a *separate governance pipeline you must actually adopt.*
- **Code/prompt drift is the central risk — and it's mitigable.** A prompt that expects a parser shape you've since changed breaks with no compile error. **Mitigation: validate output against a code-owned Zod schema** (lesson 12) so drift **fails loudly into your fail-safe** instead of mis-parsing silently. Clean ownership split: **code owns the output contract (schema); LD owns the prompt wording**, which must satisfy it.
- **You still need an in-code fallback**, so the prompt lives in two places (LD + code default for `disabled`/`degraded`/local-dev/tests). Decide which is canonical; treat the other as a deliberate safety net, not a fork.
- **Testing shifts.** You can't unit-test the live prompt; test against the fallback and rely on observability for what actually ran.

## The non-obvious lessons (the real payload)

### Edge runtime (Cloudflare Workers)

1. **Use the KV-backed *edge* SDK, not the Node SDK.** Streaming connections don't survive in a Worker. `@launchdarkly/cloudflare-server-sdk` + LD's Cloudflare integration syncing flags into a KV namespace; `init(clientSideId, KV)`. (Node runtime: standard server SDK — different wiring.)
2. **Write a *custom* OpenFeature provider.** LD's official OpenFeature provider wraps the Node streaming SDK → won't run on Workers. Write a thin `Provider` (resolveBoolean/String/Number/Object) delegating to the edge client's `variation()`. `@openfeature/server-sdk`'s default NoOp provider returns call-site defaults when LD is unconfigured → clean local-dev fallback.
6. **The edge SDK can't send events** (`sendEvents:false`, "unsupported beta") → LD's own AI Monitoring/Insights won't populate from a Worker and the LD AI tracker is a no-op there. Send metrics to PostHog (or another sink) instead. (On Node, the LD tracker works and LD's Insights/Evaluations light up.)

### Config resolution & execution

3. **AI Configs do NOT run inference.** They only manage config (model-name string, messages/instructions, parameters). You still call your own LLM (Workers AI / Anthropic / OpenAI). Decouple config-management (LD) from execution (your call).
4. **`config.model.name` slug trap — verify, then guard.** A model config has `name`/`key`/`id`. The management API (`ldcli ai-configs get-ai-config`) may show `modelName` as a slug-key (`llama-3-1-8-b-fp-8-...`), but the **served KV payload resolves it to the real provider id** (`@cf/meta/llama-3.1-8b-instruct-fp8`). **Verify per-project by reading the synced `LD-Env-<id>` KV key, not the management API.** Keep a guard (`startsWith('@')` for Workers AI ids, else fall back to a pinned constant) as a harmless safety net — but LD does manage the model end-to-end.
5. **Use Completion mode, not Agent mode, for single-shot calls.** Agent mode is gated/newer and overkill. `completionConfig` returns `messages[]` (extract the `system` message for the prompt); `agentConfig` returns `instructions`.
9. **Normalize LD's freeform params** to your provider's names (`maxTokens` → `max_tokens`, or the AI SDK's `maxOutputTokens`); default `temperature: 0` for deterministic tasks.

### Safety & failure modes

7. **Always resolve to a `source`: `disabled` / `managed` / `degraded`.**
   - `disabled` = flag off → built-in defaults, by design.
   - `managed` = live from LD.
   - `degraded` = managed expected but LD unavailable/misconfigured → apply **extra caution** (e.g. don't auto-act on the result) and surface it.

   No LD outage or empty KV should ever break the feature.
10. **Gate the whole feature behind its own boolean flag** → reversible launch.
12. **Make drift loud with a schema.** Don't hand-roll JSON extraction + lenient coercion — that *hides* drift. Validate output against a code-owned **Zod** schema; non-conforming → route to fail-safe (lesson 7). Keep **length limits OUT of the schema** (clamp/slice after) so cosmetic overruns don't fail an otherwise-valid result. **The win is the schema; the SDK is a convenience on top.**
    - **Vercel AI SDK (works on edge):** `generateText` + `Output.object({ schema })` via `workers-ai-provider` (`createWorkersAI({ binding: env.AI })`) enforces the schema and *throws* on non-conforming output → straight into your catch/fail-safe. Bonus: trivial provider swap (→ Anthropic/OpenAI). Cost ~1 MB gzipped — acceptable under CF limits if off the user's critical path (`waitUntil`). Verified: `ai@6`, `workers-ai-provider@3` (peers `ai@^6`), `zod@4`; fields `result.output` + `usage.inputTokens/outputTokens`.
    - **Zod-only (lighter):** call the model directly (`env.AI.run(...)`) and `SCHEMA.safeParse(json)`. Same drift-safety, no AI SDK. Choose only if the ~1 MB matters more than the provider abstraction.

### Observability

8. **Emit PostHog `$ai_generation`** with `$ai_model`, `$ai_provider`, `$ai_input`, `$ai_output_choices`, `$ai_input_tokens`/`$ai_output_tokens`, `$ai_latency`, `$ai_http_status`, `$ai_is_error`, plus a custom `*_config_source` prop to slice managed vs fallback. On Workers, hand-roll a fetch-based capture inside `ctx.waitUntil` (avoid `posthog-node`); on Node, the `@posthog/ai` wrapper auto-captures.
11. **For analysing the PostHog data, prefer the query API / PostHog CLI** (scope `query:read`) over the MCP for read-only work — zero context cost, least privilege. Use the MCP only when you want the rich, write-capable surface.

### Deploy trap

13. **pnpm version skew silently breaks Cloudflare Pages.** CF Pages runs a **frozen** `pnpm install` with *its own* pnpm (auto-detected) unless you pin one. If you `pnpm add/remove` locally with a different major, it can re-serialize `pnpm-lock.yaml` / `pnpm-workspace.yaml` (overrides, `minimumReleaseAgeExclude`) in a way the frozen install rejects: `ERR_PNPM_LOCKFILE_CONFIG_MISMATCH`. Presents as a deploy failure with a green local build — easy to misattribute to whatever you just added (it once caused a wrong "the AI SDK is too big" detour). Fixes: **pin `"packageManager": "pnpm@<CI-version>"` in package.json**, run all installs with that version, reproduce CI locally with `pnpm install --frozen-lockfile` before pushing. **Get the actual deploy log before theorising** — it names the real error in one line.

## What decoupling unlocks (the payoff — flag it, don't build it)

Once model/prompt/params are remote config, LD's adjacent products apply with no code change:
- **Experimentation → Experiments / Multi-armed bandits / Holdouts:** A/B or auto-optimize prompts/models against a metric.
- **Agents → Evaluations / Playgrounds / Insights:** LD-native prompt eval + iteration (Node runtime; lesson 6 re: edge).

This is the architectural argument *for* the pattern. YAGNI: mention it, don't implement it unasked.

## Scope deltas

- **Server-side flags only** here. Client-side (React SDK) is an extension, not covered.
- **Workers-first.** Node runtime differs on lessons 1, 2, 6 (use the standard server SDK; LD tracker + Insights work; PostHog wrappers auto-capture).
- **Provider-agnostic execution.** Examples target Workers AI; the AI-SDK path swaps to Anthropic/OpenAI trivially.

## Module layout to build

A clean split that has worked in practice (file names illustrative):

- `lib/flags.ts` — custom OpenFeature provider + edge client + NoOp fallback (lessons 1, 2).
- `lib/ai-config.ts` — the `disabled|managed|degraded` resolver, model-name guard, param normalization, completion-mode prompt extraction (lessons 3, 4, 5, 7, 9).
- `api/<handler>.ts` — execution via Vercel AI SDK `generateText` + `Output.object` against a code-owned Zod schema, over `workers-ai-provider`; plus the degraded-caution + PostHog path (lessons 8, 12).
- `lib/posthog-server.ts` — the `$ai_generation` emitter (lesson 8).
- `wrangler.toml` — KV binding + client-side-id var.

Keep the wiring generic; the only domain-specific piece is your output schema and what you do with the result.

> A working private reference exists in the author's `urban-emoji` repo (not public). The layout above is the portable part — you don't need the repo to follow it.
