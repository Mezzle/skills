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

## Skills

### Engineering

Adapted from Theo Browne's [tstack](https://github.com/t3dotgg/tstack) (MIT, see [NOTICE](NOTICE)).

- [babysit-pr](skills/engineering/babysit-pr/SKILL.md) — watch a PR through CI and review bots, fix the real findings.
- [council](skills/engineering/council/SKILL.md) — get review from three models on different providers, loop until they agree.
- [file-pr](skills/engineering/file-pr/SKILL.md) — file a short PR that leads with the problem, not a change inventory.
- [full-send](skills/engineering/full-send/SKILL.md) — take a change to a merged PR unattended: prove, review, file, babysit, merge.
- [full-stop](skills/engineering/full-stop/SKILL.md) — `full-send`, but stop when the PR is ready for a human to merge.
- [leaving-pr-comments](skills/engineering/leaving-pr-comments/SKILL.md) — format comments an agent posts on your behalf.
- [modernize](skills/engineering/modernize/SKILL.md) — rebase an old PR and decide whether it should still exist.
- [sol-loop](skills/engineering/sol-loop/SKILL.md) — review a change with GPT Sol in a loop until both agents agree.
- [takeover](skills/engineering/takeover/SKILL.md) — finish someone else's PR, branch or agent thread, keeping their credit.

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

Open to PRs from teammates — see [CLAUDE.md](CLAUDE.md) for repo conventions and [CONTEXT.md](CONTEXT.md) for terminology.

## License

[MIT](LICENSE)
