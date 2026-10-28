#!/usr/bin/env python3
"""Static checks and opt-in, isolated Codex or Claude skill evaluations."""
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
import urllib.parse

import yaml

from eval_results import show_results

ROOT = Path(__file__).resolve().parents[1]
PROMOTED = {'engineering', 'productivity', 'misc'}
SKILL = Path('skills/in-progress/security-review')
FIELDS = {
    'decision': {'type': 'string', 'enum': ['review', 'skip']},
    'verdict': {'type': 'string', 'enum': ['clear', 'findings', 'incomplete']},
    'access': {'type': 'string', 'enum': ['standard', 'unverified', 'verified Blue']},
    'explanation': {'type': 'string'},
    'findings': {'type': 'array', 'items': {
        'type': 'object', 'additionalProperties': False,
        'properties': {key: {'type': 'string'} for key in
                       ['id', 'file', 'evidence', 'impact', 'fix']},
        'required': ['id', 'file', 'evidence', 'impact', 'fix']}},
    'checks': {'type': 'array', 'items': {'type': 'string'}},
}
SCHEMA = {'type': 'object', 'additionalProperties': False,
          'properties': FIELDS, 'required': list(FIELDS)}


def static_checks(root):
    errors = []
    readme = (root / 'README.md').read_text()
    manifest = json.loads((root / '.claude-plugin/plugin.json').read_text())['skills']
    if len(manifest) != len(set(manifest)):
        errors.append('Duplicate plugin skill entries')
    expected = set()
    for path in sorted((root / 'skills').glob('*/*/SKILL.md')):
        relative = path.relative_to(root)
        try:
            text = path.read_text()
            match = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
            if not match:
                raise ValueError('Missing YAML frontmatter')
            metadata = yaml.safe_load(match[1])
            name = metadata['name']
            if name != path.parent.name or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
                raise ValueError('Name must match directory and use kebab-case')
            if not isinstance(metadata.get('description'), str) or not metadata['description'].strip():
                raise ValueError('Description must be a non-empty string')
            promoted = relative.parts[1] in PROMOTED
            target = relative.as_posix()
            listed = bool(re.search(r'\]\(' + re.escape(target) + r'\)', readme))
            if listed != promoted:
                errors.append(f'{relative}: README promotion mismatch')
            if promoted:
                expected.add('./' + path.parent.relative_to(root).as_posix())
        except (ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
            errors.append(f'{relative}: {exc}')
    if set(manifest) != expected:
        errors.append(f'Plugin registration mismatch: {sorted(set(manifest) ^ expected)}')
    for path in root.rglob('*.md'):
        if any(part in {'.git', 'node_modules', '.eval-results', '.venv'} for part in path.parts):
            continue
        for target in re.findall(r'\]\(([^)\s]+)\)', path.read_text()):
            parsed = urllib.parse.urlsplit(target.strip('<>'))
            if parsed.scheme or not parsed.path or parsed.path.startswith('/'):
                continue
            if not (path.parent / urllib.parse.unquote(parsed.path)).exists():
                errors.append(f'{path.relative_to(root)}: broken link {target}')
    for path in (root / 'examples').glob('*.yaml'):
        try:
            if not isinstance(yaml.safe_load(path.read_text()), dict):
                raise ValueError('Expected configuration mapping')
        except (ValueError, yaml.YAMLError) as exc:
            errors.append(f'{path.relative_to(root)}: {exc}')
    return errors


def run(command, cwd, **kwargs):
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True,
                          check=True, **kwargs)


def prepare(work, case):
    shutil.copytree(ROOT / 'tests/fixtures/security-review', work, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__'))
    app = work / 'app.py'
    fixed = app.read_text()
    vulnerable = fixed.replace("    if document['tenant'] != tenant:\n        raise PermissionError('Wrong tenant')\n", '')
    if case['variant'] == 'fixed':
        app.write_text(vulnerable)
    run(['git', 'init', '-q'], work)
    run(['git', 'add', '.'], work)
    run(['git', '-c', 'user.name=Skill Eval', '-c', 'user.email=eval@example.invalid',
         'commit', '-qm', 'Fixture baseline'], work)
    if case['variant'] == 'vulnerable':
        app.write_text(vulnerable)
    elif case['variant'] == 'fixed':
        app.write_text(fixed)
    elif case['variant'] == 'refactor':
        app.write_text(fixed.replace('document =', 'record =').replace("document[", "record["))
    elif case['variant'] == 'docs':
        (work / 'README.md').write_text('Local document service fixture.\n')
    else:
        raise ValueError(f"Unknown fixture variant: {case['variant']}")
    (work / '.agents').mkdir()
    (work / '.agents/config.yaml').write_text(yaml.safe_dump({'security_review': case['config']}))
    destination = work / '.agents/skills/security-review'
    shutil.copytree(ROOT / SKILL, destination)
    return hashlib.sha256(app.read_bytes()).hexdigest()


def grade(case, answer, work, original_hash, events=()):
    errors = []
    if not isinstance(answer, dict) or set(answer) != set(FIELDS):
        return ['Malformed result: expected exactly the response schema fields']
    for key in ['decision', 'verdict', 'access']:
        if answer[key] not in FIELDS[key]['enum']:
            errors.append(f'Invalid {key}')
    if not isinstance(answer['explanation'], str) or not answer['explanation'].strip():
        errors.append('Missing explanation')
    if not isinstance(answer['checks'], list) or not all(isinstance(x, str) for x in answer['checks']):
        errors.append('Malformed checks')
    findings = answer['findings']
    if not isinstance(findings, list):
        return errors + ['Malformed findings']
    for finding in findings:
        keys = ['id', 'file', 'evidence', 'impact', 'fix']
        if not isinstance(finding, dict) or set(finding) != set(keys) or not all(
                isinstance(finding[k], str) and finding[k].strip() for k in keys):
            errors.append('Malformed or unevidenced finding')
    expected = case['expect']
    for key in ['decision', 'verdict', 'access']:
        if answer[key] != expected[key]:
            errors.append(f"{key}: expected {expected[key]!r}, got {answer[key]!r}")
    if expected.get('finding') is True:
        if not any(isinstance(f, dict) and re.fullmatch(r'app\.py:[1-9][0-9]*', f.get('file', ''))
                   and all(f.get(k) for k in ['evidence', 'impact', 'fix']) for f in findings):
            errors.append('Missing evidenced application finding with file:line')
    elif expected.get('finding') is False and findings:
        errors.append('Unexpected security finding')
    if hashlib.sha256((work / 'app.py').read_bytes()).hexdigest() != original_hash:
        errors.append('Agent changed the application despite review-only scope')
    if expected.get('check'):
        if not answer['checks']:
            errors.append('Agent reported no validation checks')
        if not any(event.get('type') == 'item.completed'
                   and event.get('item', {}).get('type') == 'command_execution'
                   and event['item'].get('exit_code') == 0
                   and 'check_access.py' in event['item'].get('command', '')
                   for event in events if isinstance(event, dict)):
            errors.append('No successful fixture check in the agent tool trace')
        # The oracle comes from the evaluator, never from agent-editable files.
        oracle = subprocess.run(['python3', '-c',
            (ROOT / 'tests/fixtures/security-review/check_access.py').read_text()],
            cwd=work, capture_output=True, text=True)
        if oracle.returncode:
            errors.append('Independent tenant-access regression check failed')
    return errors


def case_prompt(case):
    return (f"{case['request']}\n\nUse the security-review skill at "
            '.agents/skills/security-review/SKILL.md to determine invocation and behaviour. '
            'Compare HEAD with the working tree, including untracked files. '
            'The .agents directory is evaluator setup, not part of the application change. '
            'This disposable local repository is authorised for analysis. '
            'Do not delegate, use network services, change account settings or edit application files. '
            'Run relevant local checks when called for. '
            f"\nSimulated harness capability context: {case['access']}\n"
            'Return the required JSON. decision means whether security review is called for; '
            'a skipped pass has verdict clear. access is standard for skipped reviews, '
            'unverified if required access or the selected route is unavailable. '
            'checks lists only commands actually executed; findings use file:line. '
            'Explain access limitations and routing decisions.')


def provider_command(provider, args, work, artifact, schema=SCHEMA):
    if provider == 'codex':
        command = ['codex', 'exec', '--ignore-user-config', '--ephemeral',
                   '--sandbox', 'read-only', '--cyber-access-program', 'standard',
                   '--json', '--output-schema', str(artifact / 'schema.json'),
                   '--output-last-message', str(artifact / 'answer.json'), '-']
        if args.model:
            command[2:2] = ['--model', args.model]
        if getattr(args, 'effort', None):
            command[2:2] = ['-c', f'model_reasoning_effort={json.dumps(args.effort)}']
        return command
    settings = {'sandbox': {
        'enabled': True, 'failIfUnavailable': True, 'autoAllowBashIfSandboxed': True,
        'allowUnsandboxedCommands': False, 'excludedCommands': [],
        'filesystem': {'denyWrite': [str(work)]},
        'network': {'allowedDomains': [], 'deniedDomains': ['*']},
    }}
    if getattr(args, 'claude_allow_unix_sockets', False):
        settings['sandbox']['network']['allowAllUnixSockets'] = True
    settings_path = artifact / 'claude-settings.json'
    settings_path.write_text(json.dumps(settings, indent=2))
    command = ['claude', '--print', '--verbose', '--output-format', 'stream-json',
               '--json-schema', json.dumps(schema), '--no-session-persistence',
               '--restricted', '--tools', 'Read,Glob,Grep,Bash',
               '--allowedTools', 'Read,Glob,Grep,Bash', '--permission-mode', 'dontAsk',
               '--setting-sources', '', '--settings', str(settings_path),
               '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--no-chrome']
    if args.model:
        command.extend(['--model', args.model])
    if getattr(args, 'effort', None):
        command.extend(['--effort', args.effort])
    return command


def normalise_claude(events):
    """Join actual Bash tool calls/results; never derive execution from prose."""
    calls = {}
    commands = []
    models = set()
    primary_model = None
    result = None
    for event in events:
        if event.get('type') == 'system' and event.get('subtype') == 'init' and event.get('model'):
            models.add(event['model'])
            primary_model = event['model']
        if event.get('type') == 'result':
            result = event
            models.update(event.get('modelUsage', {}).keys())
        content = event.get('message', {}).get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if event.get('type') == 'assistant' and block.get('type') == 'tool_use' and block.get('name') == 'Bash':
                tool_input = block.get('input', {})
                if tool_input.get('dangerouslyDisableSandbox'):
                    raise ValueError('Claude requested execution outside the required sandbox')
                calls[block['id']] = tool_input.get('command')
            if event.get('type') == 'user' and block.get('type') == 'tool_result':
                command = calls.pop(block.get('tool_use_id'), None)
                if not isinstance(command, str):
                    continue
                # tool_result.is_error defaults to false in the provider protocol.
                # Failed tools do not expose a reliable numeric exit status here.
                detail = event.get('tool_use_result', {})
                if not isinstance(detail, dict):
                    detail = {}
                failed = bool(block.get('is_error', False) or detail.get('interrupted')
                              or detail.get('returnCodeInterpretation'))
                exit_code = detail.get('exitCode', detail.get('exit_code'))
                if failed and exit_code == 0:
                    exit_code = None
                elif not isinstance(exit_code, int):
                    exit_code = None if failed else 0
                commands.append({'type': 'item.completed', 'item': {
                    'type': 'command_execution', 'command': command, 'exit_code': exit_code,
                    'status': 'failed' if failed else 'completed',
                    'tool_use_id': block['tool_use_id'], 'output': block.get('content'),
                }})
    if not result or result.get('subtype') != 'success' or result.get('is_error'):
        raise ValueError(f"Claude did not finish successfully: {(result or {}).get('subtype', 'missing result event')}")
    answer = result.get('structured_output')
    if not isinstance(answer, dict):
        raise ValueError('Claude returned no structured_output matching the response schema')
    metadata = {'primary_model': primary_model, 'actual_models': sorted(models), 'usage': result.get('usage'),
                'reported_cost_usd': result.get('total_cost_usd')}
    return answer, commands, metadata


def provider_output(provider, artifact):
    raw = [json.loads(line) for line in (artifact / 'raw-events.jsonl').read_text().splitlines()
           if line.strip()]
    if not all(isinstance(event, dict) for event in raw):
        raise ValueError('Provider emitted a non-object event')
    if provider == 'claude':
        answer, events, metadata = normalise_claude(raw)
        (artifact / 'answer.json').write_text(json.dumps(answer, indent=2))
    else:
        answer = json.loads((artifact / 'answer.json').read_text())
        events = raw
        metadata = {'actual_models': sorted({event['model'] for event in raw
                                            if isinstance(event.get('model'), str)})}
    (artifact / 'events.jsonl').write_text(''.join(json.dumps(event) + '\n' for event in events))
    return answer, events, metadata


def behavioural(args):
    provider = getattr(args, 'provider', 'codex')
    if not shutil.which(provider):
        raise ValueError(f'{provider} CLI is not installed or is not on PATH')
    cases = json.loads((ROOT / 'tests/cases/security-review.json').read_text())
    if args.case:
        cases = [case for case in cases if case['id'] in args.case]
        missing = set(args.case) - {case['id'] for case in cases}
        if missing:
            raise ValueError(f'Unknown cases: {sorted(missing)}')
    output_root = Path(args.output).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%d-%H%M%S-'), dir=output_root))
    results = []
    for case in cases:
        for repetition in range(args.repeat):
            artifact = output / f"{case['id']}-{repetition + 1}"
            artifact.mkdir()
            with tempfile.TemporaryDirectory(prefix='skill-eval-') as temporary:
                work = Path(temporary)
                original_hash = prepare(work, case)
                schema = artifact / 'schema.json'
                schema.write_text(json.dumps(SCHEMA))
                prompt = case_prompt(case)
                (artifact / 'prompt.txt').write_text(prompt)
                command = provider_command(provider, args, work, artifact)
                started = time.monotonic()
                errors = []
                metadata = {}
                print(f"RUN {provider} {case['id']} #{repetition + 1}", flush=True)
                with (artifact / 'raw-events.jsonl').open('w') as stdout, (artifact / 'stderr.txt').open('w') as stderr:
                    process = subprocess.Popen(command, cwd=work, stdin=subprocess.PIPE,
                                               stdout=stdout, stderr=stderr, text=True,
                                               start_new_session=True)
                    try:
                        process.communicate(prompt, timeout=args.timeout)
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
                        answer, events, metadata = provider_output(provider, artifact)
                        if (provider == 'claude' and args.model and args.model.startswith('claude-')
                                and metadata.get('primary_model') != args.model):
                            raise ValueError('Claude primary model differs from the pinned model ID')
                        errors = grade(case, answer, work, original_hash, events)
                    except (OSError, ValueError, TypeError) as exc:
                        errors = [f'Invalid or missing result: {exc}']
                (artifact / 'diff.txt').write_text(run(['git', 'diff', 'HEAD'], work).stdout)
                result = {'case': case['id'], 'repetition': repetition + 1,
                          'planned_repetitions': args.repeat,
                          'passed': not errors, 'errors': errors,
                          'elapsed_seconds': round(time.monotonic() - started, 2),
                          'provider': provider, 'requested_model': args.model,
                          'requested_effort': getattr(args, 'effort', None), **metadata,
                          'claude_allow_unix_sockets': bool(getattr(args, 'claude_allow_unix_sockets', False))
                          if provider == 'claude' else None,
                          'access_test': 'simulated; live request standard' if provider == 'codex'
                          else 'simulated OpenAI access conditions; Claude has no Daybreak programme',
                          'skill_sha256': hashlib.sha256((ROOT / SKILL / 'SKILL.md').read_bytes()).hexdigest()}
                (artifact / 'result.json').write_text(json.dumps(result, indent=2))
                results.append(result)
                print(f"{'PASS' if not errors else 'FAIL'} {case['id']} #{repetition + 1}", flush=True)
                for error in errors:
                    print(f'  {error}', flush=True)
                (output / 'summary.json').write_text(json.dumps(results, indent=2))
    (output / 'summary.json').write_text(json.dumps(results, indent=2))
    print(f'Artifacts: {output}')
    return int(any(not item['passed'] for item in results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('static')
    results = sub.add_parser('results', help='Summarise saved evals without running models')
    results.add_argument('--output', default='.eval-results')
    results.add_argument('--provider', choices=['codex', 'claude'])
    results.add_argument('--history', action='store_true', help='Also list earlier case attempts')
    results.add_argument('--json', action='store_true', help='Print a machine-readable report')
    results.add_argument('--check', action='store_true', help='Exit non-zero for failed, missing or stale evaluations')
    live = sub.add_parser('behaviour', help='Runs the selected CLI using its existing login and model allowance')
    live.add_argument('--provider', choices=['codex', 'claude'], default='codex')
    live.add_argument('--case', action='append')
    live.add_argument('--repeat', type=int, default=1)
    live.add_argument('--timeout', type=int, default=180)
    live.add_argument('--model')
    live.add_argument('--effort', help='Provider effort setting; passed without translating or substituting')
    live.add_argument('--claude-allow-unix-sockets', action='store_true',
                      help='Opt out of Claude Unix-socket filtering for hosts affected by its seccomp helper bug; filesystem/TCP restrictions stay enabled')
    live.add_argument('--output', default='.eval-results')
    args = parser.parse_args()
    try:
        if args.command == 'results':
            return show_results(args, ROOT)
        if args.command == 'static':
            errors = static_checks(ROOT)
            print('\n'.join(errors) if errors else 'PASS: frontmatter, registration, links and configuration examples')
            return bool(errors)
        if args.repeat < 1 or args.timeout < 1:
            parser.error('--repeat and --timeout must be positive')
        if args.claude_allow_unix_sockets and args.provider != 'claude':
            parser.error('--claude-allow-unix-sockets requires --provider claude')
        return behavioural(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
