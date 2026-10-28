# Testing skills

From the repository root:

```bash
./test results                    # Show saved evaluation results; no model calls
./test results --provider claude  # Claude only
./test results --history          # Include previous attempts
./test results --json             # Machine-readable report
./test results --check            # Non-zero exit for missing, failed or stale evals
./test                            # Run offline static checks and unit tests
./test claude --claude-allow-unix-sockets # Run live Claude evals on this Ubuntu host
./test codex                      # Run live Codex evals
```

The results command selects the latest settings per provider and the latest
attempt per case. It can combine cases from separate batches with identical
model, effort, socket-filter setting and skill revision. It keeps repetitions
within their original attempt and flags missing cases, unfinished repetitions
and changed skill content. Earlier attempts remain available with `--history`.
The council status is reported separately. Saved reports cover model evals;
`./test` runs the current offline checks afresh.

Install Python 3.11+ and the test dependency, then run the offline checks:

```bash
python3 -m pip install -r tests/requirements.txt
python3 scripts/skill_tests.py static
python3 -m unittest discover -s tests -v
```

Static checks cover skill frontmatter, bucket registration, local Markdown
links and YAML examples. Unit tests exercise the checker and behavioural
grader with passing and failing inputs; they do not prove agent behaviour.
CI runs both without model credentials.

## Council evaluations

Use the council matrix for confidence across model makers. Each member executes
the same cases independently; the deterministic grader scores each result.
Models do not judge one another or vote a failed case into passing.

Read `council` from the target repo's `.agents/config.yaml`, or use
`tests/council.example.yaml` explicitly. Resolve each requested model family,
route and effort through the host's current capability catalogue. Preserve exact
model pins and identify three different makers. Keep the requested settings and
their resolved targets in a JSON array, in council order:

```json
[
  {
    "requested": {"provider": "Codex", "model": "GPT Sol", "effort": "high"},
    "maker": "OpenAI",
    "target": {
      "providerInstanceId": "<catalogue provider ID>",
      "model": "<resolved exact model ID>",
      "options": {"<catalogue effort option ID>": "high"}
    },
    "blocker": null
  }
]
```

Supply all three entries. An unavailable member instead has `target: null`
and an explanatory `blocker`. These resolutions are trusted host input, not
model self-identification. The host must verify that each target and option
exists and satisfies the requested family/settings before preparing a run.

```bash
python3 scripts/council_tests.py prepare \
  --config tests/council.example.yaml \
  --resolved /path/to/host-resolutions.json --repeat 3
```

The script creates isolated workspaces and a `jobs.json` dispatch list, one job
per member, case and repetition (63 jobs for the full repeated suite). It starts
no models or provider CLIs. If any member is unavailable it records the blockers
and exits non-zero without preparing jobs. `--allow-partial` explicitly prepares
available members for diagnosis; such a run can never pass the council gate.

The host orchestrator executes `jobs.json` using supported delegate tools:

1. Start a fresh task per job, using its resolved `target` including options.
   In T3, use `delegate_task` with `role: test`; pass the workspace, prompt and
   schema paths and the answer destination. Do not share other answers, expected
   outcomes or the evaluator's `run.json`. Restrict the task to that fixture;
   the delegate runs local checks, writes its answer and starts no subagents.
2. Bound concurrency to the host's available slots. Follow completion notices;
   cancel timed-out/replaced tasks. Never treat silence as a pass. Run the same
   case in fresh tasks across members, rather than letting a council discuss it.
3. The **host**, not the evaluated model, records `execution.json` at the job's
   destination: `status` (`completed`, `failed`, `timeout` or `cancelled`),
   `task_id`, `trace_source` and the actual `target` returned by the delegate
   tool. Actual target identity and options must match the resolved request.
4. Export observed shell command results from the host's tool trace to the job's
   `events.jsonl`. Normalise each completed command to this existing grader
   format, preserving the actual command and exit code:

```json
{"type":"item.completed","item":{"type":"command_execution","command":"python3 check_access.py","exit_code":0}}
```

Codex JSONL command events already use this shape. For other providers, the
host must translate real tool results into it. Do not create events from prose
or let a tested model attest to its own execution. A missing export fails
collection rather than weakening the evidence requirement. Fixture directories
separate files and context; they are not a substitute for execution sandboxing.
The host must apply supported sandbox controls independently for every route.

After tasks finish, collect their outputs:

```bash
python3 scripts/council_tests.py collect /path/to/council-run
```

Collection writes `summary.json` and `summary.md`, retaining per-member/case
failures and routing/verdict disagreements. Missing results, failed tasks, wrong
target identity, absent tool evidence and any failed case prevent a pass. All
cases and repetitions must pass for all three makers. No live council run has
yet been verified: the current host exposes Codex and Claude, while OpenCode is
disabled. The examples are configuration templates, not claims of availability.

## Standalone CLI evaluations

With the selected CLI installed and already authenticated:

```bash
# Claude: run the full suite three times.
python3 scripts/skill_tests.py behaviour --provider claude --model opus --effort high --repeat 3

# A quicker Claude check of one case.
python3 scripts/skill_tests.py behaviour --provider claude --model opus --case tenant-leak

# Codex remains the default.
python3 scripts/skill_tests.py behaviour --case tenant-leak
python3 scripts/skill_tests.py behaviour --repeat 3
```

On this Ubuntu host, Claude's Unix-socket seccomp helper currently fails under
the stock AppArmor profile. The run command for this host uses an explicit,
per-run workaround:

```bash
python3 scripts/skill_tests.py behaviour --provider claude --model opus --effort high --claude-allow-unix-sockets --repeat 3
```

`--claude-allow-unix-sockets` skips Unix-socket filtering inside Claude's command
sandbox. Filesystem and TCP-domain restrictions remain configured, but local
Unix sockets are no longer filtered. It is off by default, recorded in results,
and never changes host policy. Use it only where that trade-off is acceptable;
see the [upstream regression](https://github.com/anthropics/claude-code/issues/43454).

Use `--provider codex|claude` to select the harness, `--model <id-or-alias>` to
select its model, `--effort <level>` to pass through its effort setting,
`--timeout <seconds>` to bound
each run, and `--output <directory>` to change artifact storage. Default timeout
is 180 seconds per case. Each repetition starts a fresh temporary Git repository
and provider session. Model IDs, aliases and effort levels are passed unchanged;
unsupported selections fail without substituting another model. Runs consume
the selected provider's model allowance and use its existing authentication.
They are opt-in, not part of CI. Ctrl-C or a timeout stops the spawned process
group; completed cases are checkpointed to the summary after each run.

Codex uses `codex exec`, a read-only sandbox, ignored user config, an ephemeral
session and explicit standard cyber treatment. Claude uses non-interactive
streaming output with a response schema, restricted mode, read/search/Bash tools,
no persistent session and no external MCP servers. Its Bash sandbox is required,
blocks fixture writes and outbound domains, and allows no unsandboxed retry.
The optional Unix-socket workaround above changes only that additional filter.
User/project settings are excluded; managed settings still apply. Neither
adapter enables Blue or changes account settings. Claude cases simulate the
OpenAI access conditions in the prompts; Claude has no Daybreak programme.

The installed `t3` CLI (checked at v0.0.46-nightly.20261015.3176) has no general
task-execution command. T3's documented `delegate_task` MCP operation requires
an active parent run. Use the standalone runner above from a terminal; use the
council job/collector workflow when an agent is orchestrating inside T3.
No T3 RPC endpoints or new top-level threads are used as a workaround.

Seven cases in `cases/security-review.json` cover a tenant leak, patch validation,
benign refactor, documentation-only change, required/optional Blue failures and
an unavailable named route. Expected answers stay in the evaluator; only the
request, fixture, configuration, skill and simulated capability context reach
the model. Skip decisions evaluate explicit routing instructions, not native
skill discovery. These cases test one pass, not full multi-round PR workflows.

Results live under `.eval-results/<timestamp>/`: prompts, response schemas,
answers, raw provider JSONL, normalised tool events, stderr, diffs and graded
summaries. Each result records provider, elapsed time, requested model/effort
and a skill fingerprint. Claude's observed model IDs, usage and reported cost
are retained when exposed. `primary_model` comes from the session-init event;
`actual_models` also includes any helper models listed in the usage report.
Costs are provider-reported estimates, not a claim
about subscription billing. Actual Bash calls are joined to their tool results;
prose about running a command never creates execution evidence. The runner does
not infer live Blue activation from model prose.

Grading checks routing, verdict, access disclosure, finding structure/location,
review-only application integrity and an independent tenant-access oracle for
the patch case. Patch validation also requires a successful `check_access.py`
command in the tool trace. Semantic quality of evidence and whether every other
reported command was actually executed still require inspecting the trace. Passing this small
suite is useful regression evidence, not a security certification.

## Extending the suite

Add fixtures under `fixtures/` and cases under `cases/`; keep expected outcomes
outside agent-visible inputs. Add grader assertions for observable outcomes
rather than exact wording. Run a known-bad answer through each new assertion
to prove it catches the regression. Direct CLI adapters support Codex and Claude;
the council path uses host delegates and normalised host tool traces. To compare
both from a terminal, run the same cases/repetitions once per provider and retain
both summaries. Two makers do not satisfy the three-maker promotion gate.

Next cases: scanner false positives, missing installed skills, changed security
assumptions after a fix and exhausted review budgets. Live Blue verification is
a separate future integration test requiring approved access and effective
programme evidence. See the [delivery plan](../docs/plans/daybreak-blue.md).

The CLI approach follows [OpenAI's skill evaluation guidance](https://developers.openai.com/blog/eval-skills).
Claude output handling follows its [headless execution documentation](https://code.claude.com/docs/en/headless).
T3 orchestration is documented in its [MCP interface](https://github.com/pingdotgg/t3code/blob/main/docs/orchestration-v2/orchestrator-mcp-server.md).

## Linux sandbox prerequisite

Before spending model allowance, check that local sandbox execution works:

```bash
codex sandbox -c 'sandbox_mode="read-only"' -- /usr/bin/true
```

On this Ubuntu host, the bundled helper failed with `bwrap: loopback: Failed
RTM_NEWADDR: Operation not permitted`. Kernel audit records showed AppArmor's
`unprivileged_userns` profile denying `net_admin` to the npm-bundled helper.
Ubuntu's existing bubblewrap policy attached to `/usr/bin/bwrap`, but that
binary was missing. Installing the distribution package fixed the same repro:

```bash
sudo apt-get install bubblewrap
```

The Mezzle dotfiles Linux development-machine hook now installs this dependency.
Claude sandbox execution also requires `socat`; the hook installs both packages.
On another Debian/Ubuntu host, install them with `sudo apt-get install bubblewrap socat`.
Global namespace restrictions remain enabled. Verify the actual failure and
existing AppArmor policy on other hosts before applying host-specific changes;
see [Codex sandbox prerequisites](https://learn.chatgpt.com/docs/sandboxing).
