"""Read saved evaluation artifacts without starting models."""
import hashlib
import json
from pathlib import Path


def settings_key(result):
    return (result.get('provider', 'codex'), result.get('requested_model'),
            result.get('requested_effort'), result.get('claude_allow_unix_sockets'),
            result.get('skill_sha256'))


def saved_results(root, expected_cases, current_skill_hash, provider=None, history=False):
    records = []
    invalid = []
    for path in Path(root).glob('*/*/result.json'):
        try:
            result = json.loads(path.read_text())
            if (not isinstance(result, dict) or not isinstance(result.get('case'), str)
                    or type(result.get('passed')) is not bool
                    or type(result.get('repetition')) is not int or result['repetition'] < 1):
                raise ValueError('Malformed case result')
            if provider and result.get('provider', 'codex') != provider:
                continue
            records.append({'result': result, 'path': str(path.resolve()),
                            'run': path.parent.parent.name, 'order': path.stat().st_mtime_ns})
        except (OSError, ValueError) as exc:
            invalid.append({'path': str(path), 'error': str(exc)})
    groups = []
    providers = sorted({record['result'].get('provider', 'codex') for record in records})
    for name in providers:
        available = [record for record in records if record['result'].get('provider', 'codex') == name]
        newest = max(available, key=lambda record: record['order'])
        key = settings_key(newest['result'])
        same_settings = [record for record in available if settings_key(record['result']) == key]
        cases = []
        for case in expected_cases:
            attempts = [record for record in same_settings if record['result']['case'] == case]
            if not attempts:
                cases.append({'case': case, 'status': 'NOT RUN', 'passed': 0, 'total': 0, 'sources': [], 'errors': []})
                continue
            latest = max(attempts, key=lambda record: record['order'])
            attempt = sorted([record for record in attempts if record['run'] == latest['run']],
                             key=lambda record: record['result']['repetition'])
            repetitions = [record['result']['repetition'] for record in attempt]
            planned = max(record['result'].get('planned_repetitions', max(repetitions)) for record in attempt)
            complete = repetitions == list(range(1, planned + 1))
            passed = sum(record['result']['passed'] for record in attempt)
            status = 'INCOMPLETE' if not complete else 'PASS' if passed == len(attempt) else 'FAIL'
            cases.append({'case': case, 'status': status, 'passed': passed, 'total': len(attempt),
                          'planned_repetitions': planned, 'sources': [record['path'] for record in attempt],
                          'errors': [error for record in attempt for error in record['result'].get('errors', [])]})
        stale = key[4] != current_skill_hash
        groups.append({'provider': name, 'model': key[1], 'effort': key[2],
                       'claude_allow_unix_sockets': key[3], 'skill_sha256': key[4], 'stale': stale,
                       'status': 'PASS' if not stale and all(case['status'] == 'PASS' for case in cases) else 'INCOMPLETE OR FAIL',
                       'cases': cases})
    council = None
    council_paths = list(Path(root).glob('council-*/summary.json'))
    if council_paths and not provider:
        path = max(council_paths, key=lambda path: path.stat().st_mtime_ns)
        try:
            data = json.loads(path.read_text())
            council = {'status': 'PASS' if data.get('passed') is True else 'INCOMPLETE OR FAIL',
                       'blockers': [member['blocker'] for member in data.get('members', []) if member.get('blocker')],
                       'source': str(path.resolve())}
        except (OSError, ValueError, AttributeError) as exc:
            invalid.append({'path': str(path), 'error': str(exc)})
    report = {'providers': groups, 'council': council, 'invalid_artifacts': invalid}
    if history:
        report['history'] = [{'run': record['run'], 'provider': record['result'].get('provider', 'codex'),
                              'case': record['result']['case'], 'repetition': record['result']['repetition'],
                              'passed': record['result']['passed'], 'source': record['path']}
                             for record in sorted(records, key=lambda record: record['order'])]
    return report


def show_results(args, repo):
    expected = [case['id'] for case in json.loads((repo / 'tests/cases/security-review.json').read_text())]
    skill_hash = hashlib.sha256((repo / 'skills/in-progress/security-review/SKILL.md').read_bytes()).hexdigest()
    report = saved_results(args.output, expected, skill_hash, args.provider, args.history)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print('Saved evals: latest settings per provider, latest attempt per case')
        for group in report['providers']:
            print(f"\n{group['provider']} / {group['model'] or 'provider default'} / effort {group['effort'] or 'default'}")
            if group['provider'] == 'claude':
                print(f"  Unix-socket filtering: {'disabled by opt-in' if group['claude_allow_unix_sockets'] else 'enabled'}")
            if group['stale']:
                print('  STALE: skill changed since these evaluations')
            for case in group['cases']:
                print(f"  {case['status']:10} {case['case']:30} {case['passed']}/{case['total']}")
                for error in case['errors']:
                    print(f'    {error}')
            print(f"  Overall: {group['status']}")
        if report['council']:
            print(f"\nCouncil: {report['council']['status']}")
            for blocker in report['council']['blockers']:
                print(f'  {blocker}')
        for invalid in report['invalid_artifacts']:
            print(f"\nInvalid artifact: {invalid['path']}: {invalid['error']}")
        if args.history:
            print('\nRun history:')
            for record in report['history']:
                print(f"  {record['run']} {record['provider']} {record['case']} #{record['repetition']} {'PASS' if record['passed'] else 'FAIL'}")
        if not report['providers'] and not report['council']:
            print(f'No saved evaluations found in {args.output}')
        print(f'\nArtifacts: {Path(args.output).resolve()}')
    exists = bool(report['providers'] or report['council'])
    failures = (any(group['status'] != 'PASS' for group in report['providers'])
                or bool(report['council'] and report['council']['status'] != 'PASS')
                or bool(report['invalid_artifacts']))
    return int(not exists or (args.check and failures))
