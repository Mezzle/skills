import argparse
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

import yaml

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import council_tests as council


class CouncilTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = self.root / 'config.yaml'
        self.requests = [
            {'provider': 'Codex', 'model': 'GPT Sol', 'effort': 'high'},
            {'provider': 'Claude', 'model': 'Claude Opus', 'effort': 'high'},
            {'provider': 'OpenCode', 'model': 'Gemini Pro', 'effort': 'high'},
        ]
        self.resolutions = [
            {'requested': requested, 'maker': maker,
             'target': {'providerInstanceId': provider, 'model': model,
                        'options': {'effort': 'high'}}, 'blocker': None}
            for requested, maker, provider, model in zip(
                self.requests, ['OpenAI', 'Anthropic', 'Google'],
                ['codex', 'claude', 'opencode'], ['sol-test', 'opus-test', 'gemini-test'])
        ]
        self.config.write_text(yaml.safe_dump({'council': self.requests}))
        self.resolved = self.root / 'resolved.json'

    def prepare(self, partial=False, repeat=1, case='tenant-leak'):
        self.resolved.write_text(json.dumps(self.resolutions))
        args = argparse.Namespace(config=self.config, resolved=self.resolved,
                                  case=[case], repeat=repeat, output=str(self.root / 'runs'),
                                  allow_partial=partial)
        with contextlib.redirect_stdout(io.StringIO()):
            return council.prepare(args)

    def record(self, directory, member=None):
        for job in council.read_json(directory / 'jobs.json'):
            if member and job['member'] != member:
                continue
            answer = {'decision': 'review', 'verdict': 'findings', 'access': 'standard',
                      'explanation': 'Tenant guard removed', 'checks': [],
                      'findings': [{'id': 'S1', 'file': 'app.py:8', 'evidence': 'Missing tenant guard',
                                    'impact': 'Cross-tenant read', 'fix': 'Restore guard'}]}
            council.write_json(job['answer'], answer)
            council.write_json(job['execution'], {'status': 'completed', 'task_id': job['id'],
                                                  'trace_source': 'test protocol stub',
                                                  'target': job['target']})
            Path(job['events']).write_text(json.dumps({'type': 'item.completed', 'item': {
                'type': 'command_execution', 'command': 'cat app.py', 'exit_code': 0}}) + '\n')

    def collect(self, directory):
        with contextlib.redirect_stdout(io.StringIO()):
            return council.collect(directory)

    def test_isolated_matrix_without_expected_answers(self):
        directory, status = self.prepare(repeat=2)
        self.assertEqual(0, status)
        jobs = council.read_json(directory / 'jobs.json')
        self.assertEqual(6, len(jobs))
        self.assertEqual(6, len({job['workspace'] for job in jobs}))
        for job in jobs:
            self.assertNotIn('expect', job)
            self.assertNotIn('expect', Path(job['prompt']).read_text())
            self.assertNotIn('run.json', Path(job['prompt']).read_text())

    def test_one_blocked_route_prevents_dispatch(self):
        self.resolutions[2].update(target=None, blocker='Provider disabled')
        directory, status = self.prepare()
        self.assertEqual(1, status)
        self.assertEqual([], council.read_json(directory / 'jobs.json'))
        self.assertFalse(self.collect(directory)[0]['passed'])

    def test_explicit_partial_cannot_pass_council(self):
        self.resolutions[2].update(target=None, blocker='Provider disabled')
        directory, status = self.prepare(partial=True)
        self.assertEqual(0, status)
        self.record(directory)
        summary, status = self.collect(directory)
        self.assertEqual(1, status)
        self.assertTrue(summary['partial'])
        self.assertEqual(2, len(summary['results']))

    def test_rejects_duplicate_makers(self):
        self.resolutions[2]['maker'] = 'openai'
        with self.assertRaisesRegex(ValueError, 'different model makers'):
            self.prepare()

    def test_rejects_resolution_for_different_request(self):
        self.resolutions[0]['requested'] = {'provider': 'Codex', 'model': 'Other'}
        with self.assertRaisesRegex(ValueError, 'does not match'):
            self.prepare()

    def test_exact_model_pins_cannot_be_substituted(self):
        self.requests[0]['model'] = 'pinned-sol-id'
        self.resolutions[0]['requested'] = copy.deepcopy(self.requests[0])
        self.config.write_text(yaml.safe_dump({'council': self.requests}))
        with self.assertRaisesRegex(ValueError, 'exact model ID'):
            self.prepare()

    def test_three_completed_members_pass(self):
        directory, _ = self.prepare()
        self.record(directory)
        summary, status = self.collect(directory)
        self.assertEqual(0, status)
        self.assertTrue(summary['passed'])
        self.assertTrue((directory / 'summary.md').exists())

    def test_majority_cannot_hide_missing_member(self):
        directory, _ = self.prepare()
        self.record(directory, member='member-1')
        self.record(directory, member='member-2')
        summary, status = self.collect(directory)
        self.assertEqual(1, status)
        self.assertFalse(summary['passed'])
        self.assertEqual(2, sum(result['passed'] for result in summary['results']))

    def test_model_identity_mismatch_fails(self):
        directory, _ = self.prepare()
        self.record(directory)
        job = council.read_json(directory / 'jobs.json')[0]
        execution = council.read_json(job['execution'])
        execution['target']['model'] = 'unasked-substitute'
        council.write_json(job['execution'], execution)
        self.assertEqual(1, self.collect(directory)[1])

    def test_unobserved_commands_do_not_count(self):
        directory, _ = self.prepare()
        self.record(directory)
        job = council.read_json(directory / 'jobs.json')[0]
        Path(job['events']).write_text('')
        self.assertEqual(1, self.collect(directory)[1])

    def test_disagreement_retained_and_failure_not_outvoted(self):
        directory, _ = self.prepare()
        self.record(directory)
        job = council.read_json(directory / 'jobs.json')[0]
        answer = council.read_json(job['answer'])
        answer.update(verdict='clear', findings=[])
        council.write_json(job['answer'], answer)
        summary, status = self.collect(directory)
        self.assertEqual(1, status)
        self.assertEqual(1, len(summary['disagreements']))

    def test_failed_task_cannot_be_approved(self):
        directory, _ = self.prepare()
        self.record(directory)
        job = council.read_json(directory / 'jobs.json')[0]
        execution = council.read_json(job['execution'])
        execution.update(status='timeout', error='No result before deadline')
        council.write_json(job['execution'], execution)
        summary, status = self.collect(directory)
        self.assertEqual(1, status)
        self.assertIn('timeout', summary['results'][0]['errors'][0])


if __name__ == '__main__':
    unittest.main()
