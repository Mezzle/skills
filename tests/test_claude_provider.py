import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import skill_tests as suite


ANSWER = {'decision': 'review', 'verdict': 'findings', 'access': 'standard',
          'explanation': 'Tenant guard removed', 'checks': ['python3 check_access.py'],
          'findings': [{'id': 'S1', 'file': 'app.py:8', 'evidence': 'Tenant comparison removed',
                        'impact': 'Cross-tenant access', 'fix': 'Restore the guard'}]}


def stream(answer=ANSWER, is_error=False):
    return [
        {'type': 'system', 'subtype': 'init', 'model': 'claude-test'},
        {'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'name': 'Bash', 'id': 'check-1',
             'input': {'command': 'python3 check_access.py'}}]}},
        {'type': 'user', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'check-1', 'content': 'fixture output',
             'is_error': is_error}]}},
        {'type': 'result', 'subtype': 'success', 'is_error': False,
         'structured_output': answer, 'modelUsage': {'claude-test': {}},
         'total_cost_usd': 0.1, 'usage': {'input_tokens': 100, 'output_tokens': 50}},
    ]


class ClaudeEventsTests(unittest.TestCase):
    def test_joins_real_tool_call_and_result(self):
        answer, commands, metadata = suite.normalise_claude(stream())
        self.assertEqual(ANSWER, answer)
        self.assertEqual('python3 check_access.py', commands[0]['item']['command'])
        self.assertEqual(0, commands[0]['item']['exit_code'])
        self.assertEqual(['claude-test'], metadata['actual_models'])
        self.assertEqual(0.1, metadata['reported_cost_usd'])

    def test_failed_tool_cannot_satisfy_patch_evidence(self):
        _, commands, _ = suite.normalise_claude(stream(is_error=True))
        self.assertIsNone(commands[0]['item']['exit_code'])

    def test_nonzero_shell_status_is_not_a_successful_tool_result(self):
        events = stream()
        events[2]['tool_use_result'] = {'returnCodeInterpretation': 'Some directories were inaccessible'}
        self.assertIsNone(suite.normalise_claude(events)[1][0]['item']['exit_code'])

    def test_explicit_numeric_exit_status_is_retained(self):
        events = stream(is_error=True)
        events[2]['tool_use_result'] = {'exitCode': 127}
        self.assertEqual(127, suite.normalise_claude(events)[1][0]['item']['exit_code'])

    def test_failed_result_cannot_claim_successful_exit(self):
        events = stream(is_error=True)
        events[2]['tool_use_result'] = {'exitCode': 0}
        self.assertIsNone(suite.normalise_claude(events)[1][0]['item']['exit_code'])

    def test_unix_socket_workaround_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(model=None, effort=None, claude_allow_unix_sockets=False)
            suite.provider_command('claude', args, root / 'work', root)
            settings = json.loads((root / 'claude-settings.json').read_text())['sandbox']
            self.assertNotIn('allowAllUnixSockets', settings['network'])
            args.claude_allow_unix_sockets = True
            suite.provider_command('claude', args, root / 'work', root)
            settings = json.loads((root / 'claude-settings.json').read_text())['sandbox']
            self.assertTrue(settings['network']['allowAllUnixSockets'])
            self.assertEqual(['*'], settings['network']['deniedDomains'])
            self.assertEqual([str(root / 'work')], settings['filesystem']['denyWrite'])

    def test_prose_never_becomes_command_evidence(self):
        events = stream()
        events[1]['message']['content'] = [{'type': 'text', 'text': 'I ran python3 check_access.py successfully'}]
        self.assertEqual([], suite.normalise_claude(events)[1])

    def test_unmatched_tool_result_is_not_evidence(self):
        events = stream()
        events[2]['message']['content'][0]['tool_use_id'] = 'unknown'
        self.assertEqual([], suite.normalise_claude(events)[1])

    def test_missing_structured_output_fails(self):
        events = stream()
        events[-1].pop('structured_output')
        with self.assertRaisesRegex(ValueError, 'structured_output'):
            suite.normalise_claude(events)

    def test_error_result_fails_even_with_answer(self):
        events = stream()
        events[-1]['subtype'] = 'error_max_structured_output_retries'
        with self.assertRaisesRegex(ValueError, 'did not finish successfully'):
            suite.normalise_claude(events)

    def test_sandbox_escape_request_is_rejected(self):
        events = stream()
        events[1]['message']['content'][0]['input']['dangerouslyDisableSandbox'] = True
        with self.assertRaisesRegex(ValueError, 'outside the required sandbox'):
            suite.normalise_claude(events)

    def test_command_builder_preserves_model_and_effort(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(model='pinned-claude-id', effort='high')
            command = suite.provider_command('claude', args, root / 'work', root)
            self.assertEqual('pinned-claude-id', command[command.index('--model') + 1])
            self.assertEqual('high', command[command.index('--effort') + 1])
            self.assertNotIn('--fallback-model', command)
            self.assertNotIn('--dangerously-skip-permissions', command)
            settings = json.loads((root / 'claude-settings.json').read_text())['sandbox']
            self.assertTrue(settings['failIfUnavailable'])
            self.assertFalse(settings['allowUnsandboxedCommands'])
            self.assertEqual([str(root / 'work')], settings['filesystem']['denyWrite'])


class ClaudeRunnerTests(unittest.TestCase):
    def exercise(self, events, exit_code=0, delay=0):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / 'claude'
            executable.write_text('#!/usr/bin/env python3\n'
                                  'import json, pathlib, sys, time\n'
                                  'prompt = sys.stdin.read()\n'
                                  'assert "expect" not in prompt\n'
                                  'assert "--restricted" in sys.argv\n'
                                  'assert "--no-session-persistence" in sys.argv\n'
                                  'settings = json.loads(pathlib.Path(sys.argv[sys.argv.index("--settings") + 1]).read_text())\n'
                                  'assert settings["sandbox"]["failIfUnavailable"]\n'
                                  'assert not settings["sandbox"]["allowUnsandboxedCommands"]\n'
                                  f'time.sleep({delay})\n'
                                  f'events = {events!r}\n'
                                  'for event in events: print(json.dumps(event), flush=True)\n'
                                  f'sys.exit({exit_code})\n')
            executable.chmod(0o755)
            args = argparse.Namespace(provider='claude', case=['tenant-leak'], repeat=1,
                                      timeout=1 if delay else 5, model='opus', effort='high',
                                      output=str(root / 'results'))
            with patch.dict(os.environ, {'PATH': str(root) + os.pathsep + os.environ['PATH']}):
                with contextlib.redirect_stdout(io.StringIO()):
                    status = suite.behavioural(args)
            summary = list((root / 'results').glob('*/summary.json'))
            self.assertEqual(1, len(summary))
            result = json.loads(summary[0].read_text())[0]
            if result['passed']:
                self.assertTrue(list((root / 'results').glob('*/*/answer.json')))
                self.assertTrue(list((root / 'results').glob('*/*/events.jsonl')))
            return status, result

    def test_claude_stream_passes_through_existing_grader(self):
        status, result = self.exercise(stream())
        self.assertEqual(0, status)
        self.assertEqual('claude', result['provider'])
        self.assertEqual(['claude-test'], result['actual_models'])

    def test_claude_exit_failure_is_not_approval(self):
        status, result = self.exercise(stream(), exit_code=2)
        self.assertEqual(1, status)
        self.assertIn('Agent exited 2', result['errors'][0])

    def test_timeout_kills_process_and_records_failure(self):
        status, result = self.exercise([], delay=30)
        self.assertEqual(1, status)
        self.assertIn('exceeded 1s timeout', result['errors'][0])


if __name__ == '__main__':
    unittest.main()
