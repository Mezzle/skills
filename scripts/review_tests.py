#!/usr/bin/env python3
"""A/B the review-loop reviewer brief: a git revision against the working tree.

Each case is a small change with one planted defect, or none. Both arms get the
same fixture, model and wrapper; only the brief rendered from SKILL.md differs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time

from skill_tests import ROOT, provider_command, provider_output, run

SKILL = 'skills/engineering/review-loop/SKILL.md'
FIXTURE = ROOT / 'tests/fixtures/review-loop'
SEVERITY = {'nit': 0, 'should': 1, 'blocker': 2}
INTENT = 'Add discounted_total to invoice.py for percentage discounts.'
FINDING = {'type': 'object', 'additionalProperties': False,
           'properties': {'id': {'type': 'string'},
                          'severity': {'type': 'string', 'enum': list(SEVERITY)},
                          'file': {'type': 'string'}, 'line': {'type': 'integer'},
                          'claim': {'type': 'string'}, 'fix': {'type': 'string'}},
           'required': ['id', 'severity', 'file', 'line', 'claim', 'fix']}
SCHEMA = {'type': 'object', 'additionalProperties': False,
          'properties': {'verdict': {'type': 'string', 'enum': ['APPROVE', 'CHANGES']},
                         'findings': {'type': 'array', 'items': FINDING}},
          'required': ['verdict', 'findings']}


def skill_text(ref):
    if ref is None:
        return (ROOT / SKILL).read_text()
    return run(['git', 'show', f'{ref}:{SKILL}'], ROOT).stdout


def render_brief(skill, work, base):
    """Fill the Round 1 brief with the same values for every arm."""
    match = re.search(r'Round 1 brief.*?\n```\n(.*?)\n```', skill, re.S)
    if not match:
        raise ValueError('No Round 1 brief block in SKILL.md')
    values = {
        '<abs path>': str(work), '<sha>': base, '<base>': base, '<intent>': INTENT,
        '<scope>': 'anything outside invoice.py and test_invoice.py',
        '<results>': 'python3 -m unittest passes',
        '<issue, path, or none>': 'SPEC.md', '<files, or none>': 'CONTRIBUTING.md',
        ' [-- <paths>]': '',
    }
    brief = match[1]
    for placeholder, value in values.items():
        brief = brief.replace(placeholder, value)
    return brief


def prompt(brief):
    return ('You are the reviewer for this local, disposable repository. Follow this brief.\n\n'
            f'{brief}\n\n'
            'Do not delegate, use network services or edit files. Return the reply as JSON: '
            'verdict, and findings with id, severity, file (relative to the repo), line, claim and fix.')


def prepare(work, case_id):
    shutil.copytree(FIXTURE / 'base', work, dirs_exist_ok=True)
    run(['git', 'init', '-q'], work)
    run(['git', 'add', '.'], work)
    run(['git', '-c', 'user.name=Skill Eval', '-c', 'user.email=eval@example.invalid',
         'commit', '-qm', 'Fixture baseline'], work)
    shutil.copytree(FIXTURE / 'variants' / case_id, work, dirs_exist_ok=True)
    return run(['git', 'rev-parse', 'HEAD'], work).stdout.strip()


def grade(case, answer):
    """Return (errors, false positives). A false positive is a blocker or should
    outside every planted range and every allowed range."""
    if not isinstance(answer, dict) or set(answer) != {'verdict', 'findings'}:
        return ['Malformed result'], 0
    findings = [f for f in answer['findings'] if isinstance(f, dict) and set(f) == set(FINDING['properties'])]
    errors = [] if len(findings) == len(answer['findings']) else ['Malformed finding']
    expect = case['expect']
    if expect['verdict'] and answer['verdict'] != expect['verdict']:
        errors.append(f"verdict: expected {expect['verdict']}, got {answer['verdict']}")

    def inside(finding, hit):
        return (Path(finding['file']).name == hit['file']
                and hit['lines'][0] <= finding['line'] <= hit['lines'][1])

    for hit in expect['hits']:
        if not any(inside(f, hit) and SEVERITY.get(f['severity'], -1) >= SEVERITY[hit['min_severity']]
                   for f in findings):
            errors.append(f"Missed {hit['file']}:{hit['lines'][0]}-{hit['lines'][1]} "
                          f"at {hit['min_severity']} or above")
    false_positives = sum(1 for f in findings if SEVERITY.get(f['severity'], 0) >= 1
                          and not any(inside(f, hit) for hit in expect['hits'] + expect.get('allow', [])))
    if not expect['hits'] and false_positives:
        errors.append(f'{false_positives} blocker/should on a clean change')
    return errors, false_positives


def evaluate(args):
    if not shutil.which(args.provider):
        raise ValueError(f'{args.provider} CLI is not installed or is not on PATH')
    cases = json.loads((ROOT / 'tests/cases/review-loop.json').read_text())
    if args.case:
        cases = [case for case in cases if case['id'] in args.case]
    arms = {'baseline': skill_text(args.baseline), 'current': skill_text(None)}
    output_root = Path(args.output).resolve() / 'review-loop'
    output_root.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%d-%H%M%S-'), dir=output_root))
    results = []
    for case in cases:
        for repetition in range(args.repeat):
            # Interleave arms so drift in the provider hits both alike.
            for arm, skill in arms.items():
                artifact = output / f"{case['id']}-{arm}-{repetition + 1}"
                artifact.mkdir()
                with tempfile.TemporaryDirectory(prefix='review-eval-') as temporary:
                    work = Path(temporary)
                    base = prepare(work, case['id'])
                    text = prompt(render_brief(skill, work, base))
                    (artifact / 'prompt.txt').write_text(text)
                    (artifact / 'schema.json').write_text(json.dumps(SCHEMA))
                    command = provider_command(args.provider, args, work, artifact, SCHEMA)
                    started = time.monotonic()
                    errors, false_positives, metadata = [], 0, {}
                    print(f"RUN {args.provider} {case['id']} {arm} #{repetition + 1}", flush=True)
                    with (artifact / 'raw-events.jsonl').open('w') as stdout, \
                            (artifact / 'stderr.txt').open('w') as stderr:
                        process = subprocess.Popen(command, cwd=work, stdin=subprocess.PIPE,
                                                   stdout=stdout, stderr=stderr, text=True,
                                                   start_new_session=True)
                        try:
                            process.communicate(text, timeout=args.timeout)
                            if process.returncode:
                                errors.append(f'Agent exited {process.returncode}; see stderr.txt')
                        except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                            try:
                                os.killpg(process.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            process.communicate()
                            if isinstance(exc, KeyboardInterrupt):
                                raise
                            errors.append(f'Agent exceeded {args.timeout}s timeout')
                    if not errors:
                        try:
                            answer, _, metadata = provider_output(args.provider, artifact)
                            errors, false_positives = grade(case, answer)
                        except (OSError, ValueError, TypeError, KeyError) as exc:
                            errors = [f'Invalid or missing result: {exc}']
                result = {'case': case['id'], 'arm': arm, 'repetition': repetition + 1,
                          'passed': not errors, 'errors': errors,
                          'false_positives': false_positives,
                          'elapsed_seconds': round(time.monotonic() - started, 2),
                          'provider': args.provider, 'requested_model': args.model,
                          'requested_effort': args.effort, 'baseline_ref': args.baseline,
                          'skill_sha256': hashlib.sha256(skill.encode()).hexdigest(),
                          **metadata}
                (artifact / 'result.json').write_text(json.dumps(result, indent=2))
                results.append(result)
                print(f"{'PASS' if not errors else 'FAIL'} {case['id']} {arm}", flush=True)
                for error in errors:
                    print(f'  {error}', flush=True)
                (output / 'summary.json').write_text(json.dumps(results, indent=2))
    report = summarise(results)
    (output / 'summary.md').write_text(report)
    print(report)
    print(f'Artifacts: {output}')
    return 0


def summarise(results):
    arms = sorted({r['arm'] for r in results})
    rows = ['| Case | ' + ' | '.join(arms) + ' |', '| --- |' + ' --- |' * len(arms)]
    for case in dict.fromkeys(r['case'] for r in results):
        cells = []
        for arm in arms:
            runs = [r for r in results if r['case'] == case and r['arm'] == arm]
            passed = sum(r['passed'] for r in runs)
            cells.append(f"{passed}/{len(runs)} pass, {sum(r['false_positives'] for r in runs)} FP")
        rows.append(f'| {case} | ' + ' | '.join(cells) + ' |')
    totals = []
    for arm in arms:
        runs = [r for r in results if r['arm'] == arm]
        cost = [r['reported_cost_usd'] for r in runs if r.get('reported_cost_usd') is not None]
        seconds = sum(r['elapsed_seconds'] for r in runs) / len(runs)
        totals.append(f"{sum(r['passed'] for r in runs)}/{len(runs)} pass, "
                      f"{sum(r['false_positives'] for r in runs)} FP, {seconds:.0f}s avg"
                      + (f', ${sum(cost):.2f}' if cost else ''))
    rows.append('| **Total** | ' + ' | '.join(totals) + ' |')
    return '\n'.join(rows) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=['codex', 'claude'], default='codex')
    parser.add_argument('--baseline', default='main', help='Git revision for the baseline arm')
    parser.add_argument('--case', action='append')
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--model')
    parser.add_argument('--effort')
    parser.add_argument('--claude-allow-unix-sockets', action='store_true')
    parser.add_argument('--output', default='.eval-results')
    args = parser.parse_args()
    try:
        return evaluate(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
