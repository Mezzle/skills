# Daybreak access

Blue is an access programme for authorised defensive security work, not a
model identity or a guarantee of better findings. Use it where vulnerability
analysis and patch validation benefit from its tailored safeguards.

Verify current model eligibility and the actual route's support using the
[official Daybreak guide](https://developers.openai.com/api/docs/guides/daybreak).
Model eligibility changes; a latest-family selection does not establish it.
Blue approval does not grant access to specialist Cyber models.

Request Blue explicitly: `scan --cyber-access-program daybreak_blue`, and
`--codex daybreak=true` on `validate` and `verify-fix`. For standard treatment,
pass `scan --cyber-access-program standard`. The scan flag is experimental and
OpenAI-provider only; a rejected flag leaves access `unverified`. An accepted
flag, a dry run or a successful scan alone does not prove Blue is active;
inspect the returned model and effective programme when the output exposes
them. Repository configuration expresses intent; it cannot provision access.

Record access as `verified Blue`, `standard`, or `unverified`, with the evidence
available. When Blue cannot be verified:

- `require_blue: true`: return `incomplete` and name the missing capability or
  access evidence. This cannot satisfy a required security review.
- `require_blue: false`: a standard review may proceed on the selected model;
  state the fallback and limitation. Never label it a Blue review. If the route
  cannot explicitly select standard treatment, report access as `unverified`.

Do not change account settings, obtain credentials, or build a new API adapter
as an implicit part of reviewing code. Report the setup needed. Authorisation
and approved internal use remain prerequisites for Daybreak work; access does
not expand the task's scope.

Sources (checked 28 October 2026):

- [Request selection, eligibility, response evidence and errors](https://developers.openai.com/api/docs/guides/daybreak)
- [Defensive use cases](https://developers.openai.com/blog/scaling-cyber-defenders-with-daybreak)
