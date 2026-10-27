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

_None yet._

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
