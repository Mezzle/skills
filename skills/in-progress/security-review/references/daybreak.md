# Daybreak access

Blue is an access programme for authorised defensive security work, not a
model identity or a guarantee of better findings. Use it where vulnerability
analysis and patch validation benefit from its tailored safeguards.

## Eligibility

Approval enables nothing on its own. Workspace and project controls default to
off, and each request selects a programme. Check current model support in the
[overview](https://help.openai.com/en/articles/20001258-openai-daybreak-trusted-access-for-cyber-overview);
it changes, and a latest-family selection does not establish it. Under Blue,
GPT-6.1 Sol, Astra and GPT-6.1 Terra keep standard safeguards (they need Red).
Blue approval grants no Red or specialist Cyber models.

## Selecting a programme

On routes that offer a Daybreak programme, select it explicitly in both
directions: `daybreak_blue` for a Blue review, `standard` for a standard one.
Omission means different things per route and model (Blue by default on some mainline models, standard from
`gpt-6.1-terra`, server defaults or a saved client choice elsewhere), so an
omitted value supports neither `verified Blue` nor `standard`.

- **Responses API:** `access_programs.cyber`. The value follows the model, not
  the approval tier: Blue-eligible mainline models take `daybreak_blue` even
  with Red approval. The response echoes `access_programs.cyber`; inspect it and
  the returned `model`.
- **Codex CLI:** `codex exec --cyber-access-program daybreak_blue|standard`
  (experimental, OpenAI provider only; its help adds "Not supported with review").
  `-c daybreak=true|false` is a toggle; `/daybreak` and `daybreak = true` in
  `config.toml` persist, and resumed or forked sessions keep their saved choice.
- **App server and Python SDK:** pass `cyberAccessProgram` on every
  `turn/start`, after checking `availableAccessPrograms.cyber` in `model/list`.
- **T3 delegates:** read the child model's options from the capability
  catalogue (today `cyberAccessProgram: standard | daybreakBlue` on Codex
  `gpt-6-sol`, default `standard`) and set it on every `delegate_task`. The
  parent's setting is not inherited. A route without the option can neither
  select nor verify Blue.

For proxied providers, the TypeScript SDK and client versions, follow the
[Codex CLI guide](https://help.openai.com/en/articles/20001607-customer-guide-using-daybreak-in-codex-cli).
Only pass settings the harness actually exposes. Repository configuration
expresses intent; it cannot provision access or invent a delegate option.

## Evidence

Record access as `verified Blue`, `standard`, or `unverified`, with the evidence.

- `verified Blue`: an explicit Blue value (`access_programs.cyber`,
  `cyberAccessProgram` or `--cyber-access-program`) succeeded on a Blue-eligible
  model, plus the echoed programme where the route exposes one. This counts on
  every listed route. The Responses API guide documents that an explicit
  selection fails without access; on Codex routes this is undocumented, so
  record that caveat with the evidence. A `daybreak=true` toggle run alone is
  not verification.
- Not evidence: a model-list entry, an ordinary reply, saved admin settings, the
  parent's setting, or a `daybreak_red` rejection on a mainline model
  (`400 invalid_access_program` fires whatever the entitlement).
- `403 access_program_not_enabled` and `400 unsupported_access_program` mean
  Blue is unavailable on that project or model; see the
  [troubleshooting guide](https://help.openai.com/en/articles/20001259-troubleshooting-openai-daybreak).
- For setup the user must check: Codex Settings → General → "Daybreak Access",
  and "Your eligibility" at chatgpt.com/cyber (individual Blue lapses without
  Advanced Account Security and a hardware key).

When Blue cannot be verified:

- `require_blue: true`: return `incomplete` and name the missing capability or
  access evidence. This cannot satisfy a required security review.
- `require_blue: false`: a standard review may proceed on the selected model;
  state the fallback and limitation. Never label it a Blue review. If the route
  cannot explicitly select standard treatment, report access as `unverified`.

## Boundaries

Do not change account settings, obtain credentials, or build a new API adapter
as an implicit part of reviewing code. Report the setup needed. Authorisation
and approved internal use remain prerequisites for Daybreak work; access does
not expand the task's scope. For third-party open-source code, a licence
permitting use, study and modification (and not forbidding analysis or reverse
engineering) authorises source analysis and testing an instance on the user's
own hardware; anyone else's deployment needs that party's explicit permission.

Sources (checked 15 November 2026):

- [Request selection, defaults, response evidence and errors](https://developers.openai.com/api/docs/guides/daybreak)
- [Programmes, model support and individual access](https://help.openai.com/en/articles/20001258-openai-daybreak-trusted-access-for-cyber-overview)
- [Troubleshooting](https://help.openai.com/en/articles/20001259-troubleshooting-openai-daybreak)
- [Codex CLI and SDKs](https://help.openai.com/en/articles/20001607-customer-guide-using-daybreak-in-codex-cli)
- [Team setup](https://help.openai.com/en/articles/20001531-openai-daybreak-set-up-access-for-your-team)
- [Defensive use cases](https://developers.openai.com/blog/scaling-cyber-defenders-with-daybreak)
