# Mini council experiment

Does a council of free models that debates for several rounds match a council
of three fast paid models answering once? Runs come from `mini council
compare`; see [the skill](../../skills/in-progress/mini-council/SKILL.md).

Real findings are the ones the user confirmed. False positives are findings the
user rejected.

| Date | Request | Arm | Members | Rounds | Wall-clock | Failures | Real | False positives | Unique real |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-28 | Review `a6913dd` (first cut of `secrets`, PR #7) | Fast council | Claude Sonnet 5.5, GPT-6 Luna, Gemini 3.5 Flash (high) | 1 | ~1.5 min | none (GLM-5.3 Highspeed dropped: no plan) | 9 / 8 of 10 | 1 / 2 | 3 / 2 |
| 2026-10-28 | Review `a6913dd` (first cut of `secrets`, PR #7) | Mini council, round 1 only | same five | 1 | ~10 min | none | 12–13 of ~17 | 4 | 7 |
| 2026-10-28 | Review `a6913dd` (first cut of `secrets`, PR #7) | Mini council | DeepSeek V4.1 Flash, GLM-5.3 Flash, Nemotron 3.5 Super, MiMo V2.6 Flash, Flint 40B (free) | 3 | ~25 min | none | 12 / 11 of 15 | 3 / 4 | 7 / 6 |

### Run 2: planted bugs

`--uninstall` and `--dry-run` added to `scripts/install_skills.py` with four planted bugs; the key was written before any review. P1 uninstall deletes every symlink; P2 `--dry-run` still renames into the backup; P3 draft-name check weakened to `'/' in name`; P4 restore picks the oldest backup. All runs one round, blind, diff only. Extras graded by the host.

| Reviewer | Arm | Planted found | Real extras | False positives | Wall-clock |
| --- | --- | --- | --- | --- | --- |
| GPT-6 Luna | Fast | 4/4 | 0 | 0 | 27s |
| Claude Sonnet 5.5 | Fast | 4/4 | 3 | 0 | 33s |
| Gemini 3.5 Flash | Fast | 3/4 (missed P2) | 1 | 0 | 68s |
| DeepSeek V4.1 Flash | Free | 4/4 | 2 | 0 | 96s |
| MiMo V2.6 Flash | Free | 4/4 | 2 | 0 | 131s |
| GLM-5.3 Flash | Free | 4/4 | 1 | 0 | 264s |
| GPT-6.1 Sol, review loop | Loop | 3/4 (missed P3 in all 3 rounds) | 7 across rounds | 0 | ~6 min, not approved |

## Notes

One line per run: what the debate changed, and which arm caught what the other
missed.

- 2026-10-28: counts are judge 1 / judge 2 (Claude Opus 5.5 both, arm labels and order swapped for judge 2), pending user confirmation. Both judges preferred the mini council for recall; both rated the fast council more precise. Gemini 3.5 Flash, added after the run, raised only two findings, both already in the fast arm. The judges disagreed on the README full-stop claim and on whether the empty-token point is shared. Ground truth from the original review (GPT-6.1 Sol, 3 rounds): (1) template file puts values on disk, both arms caught it; (2) `op`/`bw` write commands print the whole item, neither arm nor either judge caught it. Debate killed two round-1 false positives (`gh secret set` stdin, inline `op run`) and moved two members from "template is safe" to "template leaks", but it also carried three weak findings into the final list. Closed after round 3 rather than at all-HELD: members kept marking CHANGED for small rewordings.
- 2026-10-28, run 1 round 1: every real finding in the final mini-council list was already raised in round 1; debate added none, removed two false positives and turned the template leak from one member's finding into consensus. DeepSeek alone matched Sonnet. The two council-only gaps still on `main` (Bitwarden session, no-copy rule) were fixed in #9.
- 2026-10-28, run 2: on crisp code bugs every arm did well and nobody raised a false positive. Both councils found 4/4 as a group; the loop never caught the weakened draft-name check across three rounds, while every free model did. Later loop rounds drifted into design edge cases (ownership tracking, glob escaping, dangling links) rather than unfound planted bugs. Host graded the extras; answer key independent of every reviewer.
