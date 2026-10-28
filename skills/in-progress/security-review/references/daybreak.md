# Daybreak access

Blue is an access programme for authorised defensive security work, not a
model identity or a guarantee of better findings. Use it where vulnerability
analysis and patch validation benefit from its tailored safeguards.

Verify current model eligibility and the actual route's support using the
[official Daybreak guide](https://developers.openai.com/api/docs/guides/daybreak).
Model eligibility changes; a latest-family selection does not establish it.
Blue approval does not grant access to specialist Cyber models.

For Responses API routes, approved organisation/project access and model access
must be enabled. Select `access_programs.cyber: daybreak_blue` explicitly.
Inspect the returned model and effective programme when exposed. A successful
ordinary response or model-list entry alone does not prove Blue is active.

For Codex routes, verify approved workspace/user access and the Daybreak request
setting through the supported client. For delegates, check the child route's
access separately; parent settings are not evidence of inheritance. Only pass
settings the harness actually exposes. Repository configuration expresses
intent; it cannot provision access or invent a delegate option.

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
