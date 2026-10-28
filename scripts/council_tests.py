#!/usr/bin/env python3
"""Prepare isolated council jobs for the host orchestrator and collect results.

This script does not launch provider CLIs. The host resolves the configured
members and dispatches jobs through its supported delegate tools.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import tempfile
import time

import yaml

import skill_tests as suite


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + '\n')


def members_from(config, resolutions):
    """Match explicit host resolutions to requested members without substitution."""
    configured = yaml.safe_load(Path(config).read_text()).get('council', [])
    if not isinstance(configured, list) or len(configured) != 3:
        raise ValueError('Configure exactly three council members')
    if len(resolutions) != 3:
        raise ValueError('Supply one host resolution per configured member, in order')
    members = []
    for index, (requested, resolution) in enumerate(zip(configured, resolutions), 1):
        for key in ['provider', 'model']:
            if not isinstance(requested.get(key), str) or not requested[key].strip():
                raise ValueError(f'Member {index}: missing {key}')
        # The host must resolve families explicitly using its live model catalog.
        if resolution.get('requested') != requested:
            raise ValueError(f'Member {index}: resolution does not match requested configuration')
        maker = resolution.get('maker')
        if not isinstance(maker, str) or not maker.strip():
            raise ValueError(f'Member {index}: resolution must identify the model maker')
        target = resolution.get('target')
        blocker = resolution.get('blocker')
        if blocker:
            if not isinstance(blocker, str):
                raise ValueError('Blockers must be explanatory strings')
        elif not isinstance(target, dict) or not all(
                isinstance(target.get(key), str) and target[key].strip()
                for key in ['providerInstanceId', 'model']):
            raise ValueError(f'Member {index}: resolve a target or provide a blocker')
        elif not isinstance(target.get('options'), dict):
            raise ValueError(f'Member {index}: provide resolved options (or an empty mapping)')
        elif ' ' not in requested['model'] and target['model'] != requested['model']:
            raise ValueError(f'Member {index}: an exact model ID cannot be substituted')
        members.append({'id': f'member-{index}', 'requested': requested,
                        'maker': maker.strip(), 'target': target, 'blocker': blocker})
    if len({member['maker'].casefold() for member in members}) != 3:
        raise ValueError('Council must contain three different model makers')
    return members


def prepare(args):
    members = members_from(args.config, read_json(args.resolved))
    cases = read_json(suite.ROOT / 'tests/cases/security-review.json')
    if args.case:
        missing = set(args.case) - {case['id'] for case in cases}
        if missing:
            raise ValueError(f'Unknown cases: {sorted(missing)}')
        cases = [case for case in cases if case['id'] in args.case]
    output_root = Path(args.output).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=time.strftime('council-%Y%m%d-%H%M%S-'), dir=output_root))
    blockers = [member for member in members if member['blocker']]
    manifest = {'members': members, 'cases': cases, 'repeat': args.repeat,
                'jobs': [], 'blocked': bool(blockers), 'partial': bool(blockers and args.allow_partial)}
    # A missing third maker cannot silently become a two-member council.
    if blockers and not args.allow_partial:
        write_json(output / 'run.json', manifest)
        write_json(output / 'jobs.json', [])
        print(f'BLOCKED: {output}')
        for member in blockers:
            print(f"{member['id']}: {member['blocker']}")
        return output, 1
    skill_hash = hashlib.sha256((suite.ROOT / suite.SKILL / 'SKILL.md').read_bytes()).hexdigest()
    for member in members:
        if member['blocker']:
            continue
        for case in cases:
            for repetition in range(1, args.repeat + 1):
                artifact = output / member['id'] / f"{case['id']}-{repetition}"
                work = artifact / 'workspace'
                work.mkdir(parents=True)
                original_hash = suite.prepare(work, case)
                (artifact / 'prompt.txt').write_text(suite.case_prompt(case))
                write_json(artifact / 'schema.json', suite.SCHEMA)
                job = {'id': f"{member['id']}/{case['id']}-{repetition}",
                       'member': member['id'], 'case': case['id'], 'repetition': repetition,
                       'target': member['target'], 'workspace': str(work),
                       'prompt': str(artifact / 'prompt.txt'), 'schema': str(artifact / 'schema.json'),
                       'answer': str(artifact / 'answer.json'), 'events': str(artifact / 'events.jsonl'),
                       'execution': str(artifact / 'execution.json')}
                manifest['jobs'].append({**job, 'application_sha256': original_hash,
                                         'skill_sha256': skill_hash})
    write_json(output / 'run.json', manifest)
    # Dispatch only this file; run.json holds expected outcomes for the evaluator.
    write_json(output / 'jobs.json', [{key: value for key, value in job.items()
                                      if not key.endswith('_sha256')} for job in manifest['jobs']])
    print(f"Prepared {len(manifest['jobs'])} jobs: {output}")
    return output, 0


def collect(run_directory):
    directory = Path(run_directory).resolve()
    manifest = read_json(directory / 'run.json')
    cases = {case['id']: case for case in manifest['cases']}
    results = []
    for job in manifest['jobs']:
        errors = []
        answer = None
        try:
            execution = read_json(job['execution'])
            if execution.get('status') != 'completed':
                raise ValueError(f"Execution {execution.get('status', 'missing status')}: {execution.get('error', '')}")
            if not execution.get('task_id') or not execution.get('trace_source'):
                raise ValueError('Missing host task identity or trace source')
            if execution.get('target') != job['target']:
                raise ValueError('Actual host target differs from the resolved council member')
            answer = read_json(job['answer'])
            events = [json.loads(line) for line in Path(job['events']).read_text().splitlines() if line.strip()]
            if not any(isinstance(event, dict) and event.get('type') == 'item.completed'
                       and isinstance(event.get('item'), dict)
                       and event['item'].get('type') == 'command_execution'
                       and event['item'].get('exit_code') == 0 for event in events):
                raise ValueError('No successful local command in the host tool trace')
            errors = suite.grade(cases[job['case']], answer, Path(job['workspace']),
                                 job['application_sha256'], events)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors = [str(exc)]
        results.append({'member': job['member'], 'case': job['case'], 'repetition': job['repetition'],
                        'passed': not errors, 'errors': errors,
                        'decision': answer.get('decision') if isinstance(answer, dict) else None,
                        'verdict': answer.get('verdict') if isinstance(answer, dict) else None,
                        'access_test': 'simulated; not live Blue verification'})
    by_case = defaultdict(list)
    for result in results:
        by_case[(result['case'], result['repetition'])].append(result)
    disagreements = []
    for (case, repetition), items in by_case.items():
        outcomes = {(item['decision'], item['verdict']) for item in items if item['decision'] is not None}
        if len(outcomes) > 1:
            disagreements.append({'case': case, 'repetition': repetition,
                                  'outcomes': [{'member': item['member'], 'decision': item['decision'],
                                                'verdict': item['verdict']} for item in items]})
    expected_jobs = 3 * len(manifest['cases']) * manifest['repeat']
    passed = (not manifest['blocked'] and len(results) == expected_jobs
              and bool(results) and all(result['passed'] for result in results))
    summary = {'passed': passed, 'partial': manifest['partial'], 'blocked': manifest['blocked'],
               'members': manifest['members'], 'results': results, 'disagreements': disagreements}
    write_json(directory / 'summary.json', summary)
    rows = ['# Council evaluation', '', f"Overall: {'PASS' if passed else 'INCOMPLETE OR FAIL'}", '',
            '| Member | Model | Passed | Total | Blocker |', '|---|---|---:|---:|---|']
    for member in manifest['members']:
        items = [item for item in results if item['member'] == member['id']]
        rows.append(f"| {member['maker']} | {member['requested']['model']} | "
                    f"{sum(item['passed'] for item in items)} | {len(items)} | {member['blocker'] or ''} |")
    rows.extend(['', 'See summary.json for case failures and disagreements. A majority cannot override a failed case.', ''])
    (directory / 'summary.md').write_text('\n'.join(rows))
    print(f"{'PASS' if passed else 'INCOMPLETE OR FAIL'}: {directory / 'summary.json'}")
    return summary, 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    setup = sub.add_parser('prepare')
    setup.add_argument('--config', type=Path, default=suite.ROOT / '.agents/config.yaml')
    setup.add_argument('--resolved', type=Path, required=True, help='Host-verified target resolutions JSON')
    setup.add_argument('--case', action='append')
    setup.add_argument('--repeat', type=int, default=1)
    setup.add_argument('--output', default='.eval-results')
    setup.add_argument('--allow-partial', action='store_true', help='Explicitly prepare available members; never a council pass')
    finish = sub.add_parser('collect')
    finish.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            if args.repeat < 1:
                parser.error('--repeat must be positive')
            return prepare(args)[1]
        return collect(args.run_directory)[1]
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
