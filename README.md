# Skills

Personal Claude Code skills. Copy what's useful — they're small, opinionated, and meant to be adapted.

## Install

Via [skills.sh](https://skills.sh):

```bash
npx skills@latest add Mezzle/skills
```

Or copy any skill directory into your `~/.claude/skills/`:

```bash
git clone git@github.com:Mezzle/skills.git
cp -r skills/skills/<bucket>/<skill-name> ~/.claude/skills/
```

For an editable local installation in both Codex and Claude Code:

```bash
python3 scripts/install_skills.py --draft security-review
```

This links promoted skills and the selected draft to this checkout, preserving
replaced installations under `~/.local/state/mezzle-skills/backups/`. Omit
`--draft security-review` to install promoted skills only. Keep the checkout in
place; moving it requires rerunning the installer. Skills become available on
your next turn. Installing the draft does not enable automatic security review
or provision Daybreak access; use the configuration below when needed.

## Skills

### Engineering

Adapted from Theo Browne's [tstack](https://github.com/t3dotgg/tstack) (MIT, see [NOTICE](NOTICE)).

- [babysit-pr](skills/engineering/babysit-pr/SKILL.md) — watch a PR through CI and review bots, fix the real findings.
- [council](skills/engineering/council/SKILL.md) — get review from three models on different providers, loop until they agree.
- [file-pr](skills/engineering/file-pr/SKILL.md) — file a short PR that leads with the problem, shows the change in a visual, and gives evidence and merge danger. The description shape is adapted from Matt Pocock's [`pr`](https://github.com/mattpocock/skills) skill (MIT, see [NOTICE](NOTICE)).
- [full-send](skills/engineering/full-send/SKILL.md) — take a change to a merged PR unattended: prove, review, file, babysit, merge.
- [full-stop](skills/engineering/full-stop/SKILL.md) — `full-send`, but stop when the PR is ready for a human to merge.
- [leaving-pr-comments](skills/engineering/leaving-pr-comments/SKILL.md) — format comments an agent posts on your behalf.
- [modernize](skills/engineering/modernize/SKILL.md) — rebase an old PR and decide whether it should still exist.
- [review-loop](skills/engineering/review-loop/SKILL.md) — have a model from another provider review a change for bugs, spec and standards in a loop until both agree. The spec and standards axes are adapted from Matt Pocock's [`code-review`](https://github.com/mattpocock/skills) skill (MIT, see [NOTICE](NOTICE)).
- [secrets](skills/engineering/secrets/SKILL.md) — read credentials from 1Password or Bitwarden at runtime without leaking them.
- [takeover](skills/engineering/takeover/SKILL.md) — finish someone else's PR, branch or agent thread, keeping their credit.

- [wayfinder](skills/engineering/wayfinder/SKILL.md) — map a large effort as decision tickets, routing ready work to humans or agents. Adapted from Matt Pocock’s `wayfinder` (MIT, see [NOTICE](NOTICE)).

## Configuration

The PR and review skills read `.agents/config.yaml` at the root of the repo they run in. Every key is optional. Without the file they fall back to their defaults and work out what they can from the repo.

| Key | Used by | Meaning |
|---|---|---|
| `tracker` | file-pr, full-send, review-loop | `jira`, `github`, `linear`, or `none`. Without it, inferred from recent PRs. |
| `review_bots.request` | file-pr, babysit-pr | Bots to request a review from on filing and after every push, e.g. `copilot`. |
| `review_bots.wait_for` | babysit-pr | Bots that must review the head before the PR is ready. Without it, `pr-wait` works it out from the PR. |
| `reviewer` | review-loop | `provider`, `model`, optional `effort`. Defaults to the latest GPT Sol. |
| `council` | council | A list of three `provider` / `model` / `effort` entries. Defaults to the latest flagship from three makers. |
| `secrets` | secrets; inherited by full-send/full-stop | `manager`: `1password` or `bitwarden`, optional default `vault`. Without it, the user's instructions decide, else the agent asks. |
| `security_review` | security-review, review-loop, babysit-pr; inherited by full-send/full-stop | Opt-in draft security review. See the setup below. |

A model family such as `GPT Sol` means the latest in that family. An exact ID pins it. Examples: [Chemist4U](examples/config.chemist4u.yaml), [personal](examples/config.personal.yaml).

### Draft security review

The security-review draft is not included in the plugin or normal installation.
To try it, copy `skills/in-progress/security-review/` into your harness's skills
directory, including `references/`. The source checkout's workflow hooks can
also read it directly. Enable it in the target repo's `.agents/config.yaml`:

```yaml
security_review:
  mode: auto # manual (default) | auto for changes to trust boundaries/findings
  access_program: daybreak_blue # standard (default) | daybreak_blue
  require_blue: false # true makes missing verified Blue access a blocker
  # Optional provider, model and effort; explicit user choices take precedence.
  # Omit them to use the current model; verify its Blue eligibility separately.
```

These are skill settings, not harness or API fields. They neither grant access
nor change the general reviewer or council. An explicit security-review request
also invokes the skill in manual mode. Automatic invocation requires a changed
security assumption or substantive security finding; ordinary edits keep the
existing workflow. If the skill is needed but missing, the workflow reports an
incomplete security review. With no settings or request, behaviour is unchanged.

Blue use requires an eligible model, approved access and an enabled request path.
`require_blue: false` permits a disclosed standard review if Blue is unavailable;
`true` requires `access_program: daybreak_blue` and verified access. See the
[delivery and evaluation plan](docs/plans/daybreak-blue.md) for promotion gates
and planned extensions.

## Structure

```
skills/
  <bucket>/
    <skill-name>/
      SKILL.md      # behavior + frontmatter
```

Buckets follow the same convention as Matt Pocock's [skills](https://github.com/mattpocock/skills) repo:

- `productivity/` — non-code workflow tools
- `engineering/` — daily code work
- `personal/` — tied to my own setup, not promoted
- `in-progress/` — drafts not yet ready to ship

Only skills under `productivity/`, `engineering/`, and `misc/` are listed in the top-level `README.md` and `.claude-plugin/plugin.json`.

## Contributing

Run the [skill tests](tests/README.md) before changing skill behaviour. Offline
checks run in CI. The optional council matrix exercises security-review across
three model makers in separate fixture repositories; a Codex CLI runner remains
available for single-model checks, alongside a standalone Claude CLI adapter.

Open to PRs from teammates — see [CLAUDE.md](CLAUDE.md) for repo conventions and [CONTEXT.md](CONTEXT.md) for terminology.

## License

[MIT](LICENSE)
