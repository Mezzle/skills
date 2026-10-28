---
name: mini-council
description: Trigger this if the user says 'mini council'.
---

# Mini council

An experiment: a council of free models that debates for several rounds
instead of answering once. Same job as `council` (review or feedback on the
user's request), cheaper members, more chat. When the user says
`mini council`, this skill applies and `council` does not.

## Members

Pick in this order:

1. Members the user names in the request.
2. The `mini_council.members` list in `.agents/config.yaml`. Same entry shape
   as `council`: `provider`, `model`, optional `effort`.
3. Every free model in the catalogue, one per model family, up to five. In T3
   Code, `orchestrator_capabilities` with `search: "free"`; free IDs end in
   `-free`.

All members can share one route; diversity comes from model families, not
makers. The keys are shown in `examples/config.mini-council.yaml` in the
skills repo. OpenCode exposes reasoning as `variant`, not `effort`: pass a
configured `effort` as `variant`; without one, use the highest offered. Some
free models expose no options; send none.

Free tiers rate-limit and drop out. Report every member that fails. Carry on
while three or more remain; below three, stop and report.

Free routes may log or train on inputs. Send only material the user is happy
to share publicly; ask first when the request touches private code or data.

## Debate

Start one fresh `delegate_task` per member per round, in parallel, read-only.
Carry the debate in the task text; each round is a new task.

1. **Opening.** Each member gets the request and context, and answers
   independently: findings, a recommendation, and a score out of 10 for code
   review.
2. **Rebuttal rounds.** Each member gets its own last position plus the
   others', labelled `Member A`, `Member B`, … with model names removed. For
   every other member's point it must _concede_, _rebut_ with a reason, or
   _build_ on it, then restate its position and score. Ask it to mark
   `CHANGED` or `HELD`.
3. **Close.** Stop after a round where every member marks `HELD`, or after
   `mini_council.max_rounds` rounds (default 4, counting the opening).

Then summarise as `council` does: useful findings, live disagreements,
recommended next steps. Give findings that survived rebuttal more weight than
ones only a single member raised.

Report the debate itself; it is the point of the experiment:

```markdown
## Mini council

Rounds: 3 (closed: all held)

| Member | R1 | R2 | R3 |
| --- | --- | --- | --- |
| DeepSeek V4.1 Flash | 6/10 | 7/10 CHANGED | 7/10 HELD |
| GLM-5.3 Flash | 8/10 | 7/10 CHANGED | 7/10 HELD |
| Nemotron 3.5 Super | 5/10 | 5/10 HELD | 5/10 HELD |

Moves:
- GLM conceded the race in `sync.ts:42` after DeepSeek's rebuttal.
- Nemotron held its objection to the retry loop; nobody answered it.
```

If a member gives no score, write `no score`. PR handling, the fix-and-review
loop and the scope guard follow `council` unchanged.

## Compare

When the user says `mini council compare`, run the same request through two
arms and record which did better.

- **Arm A**: invoke `council`, naming as its members the trio in
  `mini_council.compare_with`. Without it, name the fastest strong model from
  three makers at `high`, for example Claude Sonnet, GPT Luna and Gemini
  Flash.
- **Arm B**: the mini council above.

Run both arms in parallel, read-only, on identical request text and context.
Change nothing until the user has confirmed the findings below. Record
wall-clock time, rounds and member failures per arm.

Then start one judge `delegate_task` on the strongest model available (Claude
Opus by default) at high effort. Give it both arms' final summaries labelled
`Arm X` and `Arm Y` in random order, with model names removed. It merges the
findings into one deduplicated list and marks each with the arms that raised
it, plus `likely real` or `likely false positive`. Then show the user the
unblinded list and ask them to confirm which findings are real; their verdict
overrides the judge.

Append the result to `docs/experiments/mini-council.md` in the skills repo
if it is checked out, else give it in the final reply. Use the table there.
