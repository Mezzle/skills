---
name: council
description: Trigger this if the user says 'council'.
---

# Council

Bring in three delegates to help with the user's request, usually for review
or feedback. Use one strong model from each of three different model makers,
at the effort picked below. Two members can share a route: GPT and Gemini
can both run through Copilot.

Pick the members in this order:

1. Members the user names in the request.
2. The `council` list in `.agents/config.yaml` at the repo root. Each entry has
   a `provider` (the route, as the harness names it), a `model`, and an
   optional `effort`. A model family such as `GPT Astra` means the latest model
   in that family. An exact ID pins it.
3. Each maker's pick from the [Artificial Analysis Intelligence Index vs
   cost per task](https://artificialanalysis.ai/#intelligence) chart. Consider
   only `high` and `xhigh` efforts; never `max`, which overthinks. Take the
   cheapest model and effort within 1 point of that maker's best score.
   Snapshot, 22 November 2026:

   | Maker | Pick | Index | Cost per task | Passed over |
   | --- | --- | --- | --- | --- |
   | Anthropic | Claude Fable (high) | 62 | $9.08 | Fable xhigh 62, $14.83; Opus xhigh 57, $6.05 |
   | OpenAI | GPT Astra (xhigh) | 62 | $2.52 | Astra high 60, $2.07; Sol xhigh 56, $0.65 |
   | Google | Gemini Neon (high) | 60 | $3.74 | Neon xhigh 61, $6.44; Carbon high 60, $7.76 |

   If a maker has released a model since the snapshot, check the chart again.

Claude Fable requires 30-day data retention. Get explicit consent before
sending it code or data. If consent is declined or unavailable, use Claude
Opus at `xhigh` and report the fallback.

In T3 Code, use `orchestrator_capabilities` to resolve the models, then
`delegate_task` to start one delegate per model in parallel. Elsewhere, use
the harness's subagent tools. If you cannot reach three makers, or a named or
configured member is unavailable, report it instead of substituting.

Give each delegate the request and relevant context. For review or feedback,
keep their work read-only. Collect their responses and summarise the useful
findings, disagreements, and recommended next steps.

For a code review, ask each delegate for a score out of 10.
Count each full review pass as one round.
A fresh review after fixes starts a new round.

If the work ends in a pull request, put the results in the PR description.
Put this section before the model and harness line at the end:

```markdown
## Council review

Rounds: 2

| Delegate | Round 1 | Round 2 |
| --- | --- | --- |
| Claude Fable | 7/10 | 9/10 |
| GPT Astra | 8/10 | 10/10 |
| Gemini Neon | 7/10 | 9/10 |
```

If a delegate gives no score, write `no score`. Do not invent one.
If the PR is open, edit the description. Do not post a comment for this.
If there is no PR, put the same results in the final reply only.

If you agree with their recommendations, make the changes and request a fresh
review after. Continue until all delegates are satisfied, for at most three
rounds, or the number the user names. Stop early if a round only repeats
findings you already declined with a reason.

At the cap, stop. Do not start another round or merge. Report the findings
still open, each delegate's last score, and that the approach may need
rethinking. The user decides what happens next.

Do not let repeated reviews result in scope creep. It is your job to fight to
keep scope limited.
