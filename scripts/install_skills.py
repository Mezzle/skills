#!/usr/bin/env python3
"""Link this checkout's promoted skills and explicitly selected drafts locally."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install(home, drafts):
    manifest = json.loads((ROOT / '.claude-plugin/plugin.json').read_text())
    sources = [ROOT / path for path in manifest['skills']]
    for name in drafts:
        if Path(name).name != name or name in {'.', '..'}:
            raise ValueError(f'Invalid draft name: {name}')
        sources.append(ROOT / 'skills/in-progress' / name)
    for source in sources:
        if not (source / 'SKILL.md').is_file():
            raise ValueError(f'Missing skill: {source}')
    backup = home / '.local/state/mezzle-skills/backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    for harness in ['codex', 'claude']:
        destination = home / f'.{harness}/skills'
        destination.mkdir(parents=True, exist_ok=True)
        for source in sources:
            target = destination / source.name
            if target.is_symlink() and target.resolve() == source.resolve():
                print(f'Current: {target}')
                continue
            if target.exists() or target.is_symlink():
                saved = backup / harness / source.name
                saved.parent.mkdir(parents=True, exist_ok=True)
                target.rename(saved)
                print(f'Backup: {saved}')
            target.symlink_to(source.resolve(), target_is_directory=True)
            print(f'Linked: {target} -> {source.resolve()}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draft', action='append', default=[], help='Explicitly opt into an in-progress skill')
    parser.add_argument('--home', type=Path, default=Path.home(), help='Alternate home for installation checks')
    args = parser.parse_args()
    try:
        install(args.home.expanduser().resolve(), args.draft)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Installation failed: {exc}\n')


if __name__ == '__main__':
    main()
