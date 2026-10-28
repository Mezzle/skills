# Daybreak Blue delivery plan

Status: draft skill and opt-in workflow hooks implemented. Initial behavioural
run: six cases passed, documentation-only case timed out after 180 seconds.
Live Blue access evaluation remains pending. No Blue provisioning or account
changes are included.

The [test suite](../../tests/README.md) now provides static checks, grader unit
tests, seven opt-in Codex cases and an isolated council matrix/collector.
Council preparation requires three resolved makers and records unavailable
routes as blockers; a partial run cannot satisfy the promotion gate.
Agent behaviour and live Blue activation
remain separate validation steps; the initial cases simulate unavailable access.

On 28 October 2026, installing Ubuntu's system `bubblewrap` package resolved
the host's sandbox startup failure without changing AppArmor policy or global
namespace restrictions. Read-only filesystem and outbound-network restrictions
were checked directly. The rerun passed tenant-leak detection, patch validation,
benign-refactor routing, required/optional Blue fallback and unavailable named
route handling. The documentation-only case returned no result before its
timeout; the promotion gate remains unmet. Artifacts are retained locally under
`.eval-results/20261028-152500-qhmr96fn/`.

Standalone Claude CLI support was added on the same date. All seven cases passed
once on Claude Opus 5.5 at high effort, in two batches. This Ubuntu host required
the explicit `--claude-allow-unix-sockets` workaround for Claude's seccomp-helper
regression; that result does not establish Unix-socket filtering. Filesystem and
TCP-domain restrictions remained configured. Artifacts are under
`.eval-results/20261028-161335-3l2ppyop/` and
`.eval-results/20261028-161453-610aj1d1/`. Three repetitions per maker, an available
third maker and live Blue verification are still needed for the promotion gate.

## Delivered

- `skills/in-progress/security-review/`: security review, finding triage and
  patch validation, with conditional Daybreak access guidance.
- `review-loop`: one shared scope, ledger and round budget for security and
  general review. Existing reviewer selection remains intact.
- `full-send` and inherited `full-stop`: security results feed the readiness
  gate, without a duplicate loop.
- `babysit-pr`: targeted security-finding triage and rechecks.
- `file-pr`: evidence and access limitations carried into the description.
- README setup and commented examples; existing configurations remain unchanged.

The draft stays outside the plugin manifest and promoted skills list until the
evaluation below passes. Install the whole skill directory separately to trial
it in another repository. Configuration alone does not install it.

## Next: evaluate the draft

Use disposable local repositories and known fixtures. Keep the case inputs and
expected outcomes separately so a future evaluator can work without seeing the
answers. Record each run's revision, prompt, base/head, selected route/model,
observed access programme, findings, check output, elapsed time and usage when
exposed. Never infer token cost from missing usage data.

Run these cases before promotion:

- Known authorisation or tenant-isolation bug: identify the reachable path,
  prerequisites and impact, then demonstrate a failing regression check.
- Fixed variant: the regression check passes and legitimate access still works;
  recheck resolves the original stable finding ID.
- Benign refactor near authentication: auto routing skips it when no security
  assumption changes; no security findings are invented.
- False-positive scanner finding: inspect the existing control and dismiss with
  source evidence rather than changing safe code to appease the scanner.
- Ordinary UI/docs edit: enabling auto mode creates no security pass.
- Blue unavailable or effective access unexposed: optional mode discloses the
  fallback; required mode returns incomplete and blocks readiness.
- Named reviewer or unsupported configured route: preserve the selected model;
  report unavailability without substituting or silently dropping the review.
- Security fix during babysitting: invalidate affected evidence and recheck the
  current behaviour; reuse unaffected findings without another full audit.
- Copied installation missing the draft: report incomplete when the hook fires;
  default/manual workflows without a security request remain unchanged.
- Round budget exhausted with an unresolved material finding: return findings
  or incomplete, never an approval based on elapsed rounds.

Where approved access is available, run the same defensive cases on the same
model with standard and verified Blue treatment. This separates the value of
the skill from the value of the access programme. Compare supported findings,
false positives, completed patch validations, refusal-related interruptions,
latency and observed cost. Do not assume Blue increases reasoning quality.

Promotion gate: all routing/access cases behave as specified; known security
bugs are supported by evidence; fixed/benign cases produce no material false
positives; patch checks demonstrate the vulnerable/fixed distinction. Record
these outcomes independently across three model makers, preserving case-level
failures and disagreements rather than averaging them away. Repeat the suite
three times per member to check consistency. A single-model smoke run is not
the council gate. The current host has only two enabled makers, so the live
council run remains blocked pending an available authorised third route. Record
live access evidence separately. If it cannot be obtained, leave Blue support
marked unverified and keep the skill in draft.

## Then: promote and tighten integration

After the gate passes:

1. Move the skill to `skills/engineering/security-review/` and update source
   pointers. Add its entry to README's Engineering list and the plugin manifest
   in the same change. Verify installation includes its reference file.
2. Publish the evaluation record and revise only behaviours that failed cases.
3. Trial opt-in auto mode on real security-sensitive PRs. Retain manual defaults
   until the routing decisions and review overhead justify broader adoption.

## Later: extend only against demonstrated needs

- `takeover` / `modernize`: route unfinished security findings and conflict fixes
  that alter controls through the same review; evaluate evidence invalidation
  after rebases before adding these hooks.
- `council`: add a security brief to an already eligible member when needed,
  retaining explicit member choices and the different-maker rule. Blue is an
  access setting, not a fourth reviewer or another maker.
- Incident response: design a separate skill around investigation scope,
  evidence handling and containment permissions after real incident use cases
  establish the inputs and completion criteria.
- Malware analysis: assess a separate workflow only with an appropriate isolated
  analysis environment and authorised samples. Keep it out of ordinary PR work.
- Harness support: add an adapter only if a supported integration exposes access
  selection and effective-programme evidence. Do not invent delegate options or
  add a credential-handling script to compensate for missing harness support.

For each extension, require a real triggering case, a bounded workflow, realistic
evaluation and a documented completion criterion before promotion. Revisit model
eligibility using the official guide when adding a route or changing models.

## Sources

- [Daybreak request selection and access verification](https://developers.openai.com/api/docs/guides/daybreak)
- [Defensive use cases and tier distinctions](https://developers.openai.com/blog/scaling-cyber-defenders-with-daybreak)

Documentation checked 28 October 2026. Implementation does not establish that
the current user, model or harness has approved and active Blue access.
