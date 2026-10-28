import copy
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import skill_tests as runner
CASES = json.loads((runner.ROOT / 'tests/cases/security-review.json').read_text())


class GraderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.case = copy.deepcopy(CASES[0])
        self.original_hash = runner.prepare(self.work, self.case)
        self.answer = {
            'decision': 'review', 'verdict': 'findings', 'access': 'standard',
            'explanation': 'The tenant guard was removed.', 'checks': [],
            'findings': [{'id': 'S1', 'file': 'app.py:8',
                          'evidence': 'Caller-controlled document_id indexes records without a tenant check.',
                          'impact': 'Alice can read Bob records.', 'fix': 'Restore the tenant guard.'}],
        }

    def grade(self):
        return runner.grade(self.case, self.answer, self.work, self.original_hash)

    def test_accepts_evidenced_finding(self):
        self.assertEqual([], self.grade())

    def test_rejects_missed_vulnerability(self):
        self.answer.update(verdict='clear', findings=[])
        self.assertTrue(self.grade())

    def test_rejects_false_blue_claim(self):
        self.answer['access'] = 'verified Blue'
        self.assertTrue(self.grade())

    def test_rejects_unevidenced_finding(self):
        self.answer['findings'][0]['evidence'] = ''
        self.assertTrue(self.grade())

    def test_rejects_scope_violation(self):
        (self.work / 'app.py').write_text('pass\n')
        self.assertIn('Agent changed the application despite review-only scope', self.grade())

    def test_rejects_malformed_result(self):
        self.assertTrue(runner.grade(self.case, [], self.work, self.original_hash))

    def test_required_access_cannot_pass_clear(self):
        self.case = copy.deepcopy(CASES[4])
        self.answer.update(verdict='clear', access='unverified', findings=[])
        self.assertTrue(self.grade())

    def test_fixture_oracle_detects_vulnerable_version(self):
        result = subprocess.run(['python3', 'check_access.py'], cwd=self.work, capture_output=True)
        self.assertNotEqual(0, result.returncode)

    def test_fixed_fixture_oracle_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            case = CASES[1]
            original_hash = runner.prepare(work, case)
            answer = dict(self.answer, verdict='clear', findings=[], checks=['python3 check_access.py'])
            events = [{'type': 'item.completed', 'item': {'type': 'command_execution',
                       'command': 'python3 check_access.py', 'exit_code': 0}}]
            self.assertEqual([], runner.grade(case, answer, work, original_hash, events))

    def test_reported_check_without_tool_evidence_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            case = CASES[1]
            original_hash = runner.prepare(work, case)
            answer = dict(self.answer, verdict='clear', findings=[], checks=['python3 check_access.py'])
            self.assertIn('No successful fixture check in the agent tool trace',
                          runner.grade(case, answer, work, original_hash))

    def test_patch_validation_requires_reported_check(self):
        self.case = CASES[1]
        self.answer.update(verdict='clear', findings=[])
        self.assertTrue(self.grade())


class StaticTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(runner.ROOT / 'skills', self.root / 'skills')
        shutil.copytree(runner.ROOT / '.claude-plugin', self.root / '.claude-plugin')
        shutil.copytree(runner.ROOT / 'examples', self.root / 'examples')
        shutil.copytree(runner.ROOT / 'docs', self.root / 'docs')
        for name in ['README.md', 'CLAUDE.md', 'CONTEXT.md', 'NOTICE', 'LICENSE']:
            shutil.copy2(runner.ROOT / name, self.root / name)
        # README also links to the test guide.
        (self.root / 'tests').mkdir()
        source = runner.ROOT / 'tests/README.md'
        if source.exists():
            shutil.copy2(source, self.root / 'tests/README.md')

    def test_valid_repository(self):
        self.assertEqual([], runner.static_checks(self.root))

    def test_missing_registration(self):
        path = self.root / '.claude-plugin/plugin.json'
        data = json.loads(path.read_text())
        data['skills'].pop()
        path.write_text(json.dumps(data))
        self.assertTrue(runner.static_checks(self.root))

    def test_broken_reference(self):
        with (self.root / 'README.md').open('a') as file:
            file.write('\n[missing](missing.md)\n')
        self.assertTrue(runner.static_checks(self.root))

    def test_invalid_frontmatter(self):
        path = self.root / runner.SKILL / 'SKILL.md'
        path.write_text(path.read_text().replace('name: security-review', 'name: wrong'))
        self.assertTrue(runner.static_checks(self.root))

    def test_invalid_yaml_example(self):
        (self.root / 'examples/broken.yaml').write_text('key: [')
        self.assertTrue(runner.static_checks(self.root))


class RunnerTests(unittest.TestCase):
    def exercise(self, response, exit_code=0):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / 'codex'
            # A protocol stub tests subprocess/artifact handling, never model behaviour.
            executable.write_text('#!/usr/bin/env python3\n'
                                  'import json, pathlib, sys\n'
                                  'prompt = sys.stdin.read()\n'
                                  'assert "expect" not in prompt\n'
                                  'assert "--sandbox" in sys.argv\n'
                                  'assert sys.argv[sys.argv.index("--sandbox") + 1] == "read-only"\n'
                                  f'answer = {response!r}\n'
                                  'pathlib.Path(sys.argv[sys.argv.index("--output-last-message") + 1]).write_text(json.dumps(answer))\n'
                                  'print(json.dumps({"type": "turn.completed"}))\n'
                                  f'sys.exit({exit_code})\n')
            executable.chmod(0o755)
            args = argparse.Namespace(case=['tenant-leak'], repeat=1, timeout=5,
                                      model=None, output=str(root / 'results'))
            with patch.dict(os.environ, {'PATH': str(root) + os.pathsep + os.environ['PATH']}):
                with contextlib.redirect_stdout(io.StringIO()):
                    status = runner.behavioural(args)
            summary = list((root / 'results').glob('*/summary.json'))
            self.assertEqual(1, len(summary))
            result = json.loads(summary[0].read_text())[0]
            self.assertTrue(list((root / 'results').glob('*/*/raw-events.jsonl')))
            return status, result

    def test_runner_records_passing_protocol_response(self):
        response = {'decision': 'review', 'verdict': 'findings', 'access': 'standard',
                    'explanation': 'Tenant guard removed', 'checks': [],
                    'findings': [{'id': 'S1', 'file': 'app.py:8', 'evidence': 'Missing guard',
                                  'impact': 'Cross-tenant read', 'fix': 'Restore guard'}]}
        status, result = self.exercise(response)
        self.assertEqual(0, status)
        self.assertTrue(result['passed'])

    def test_agent_failure_is_not_approval(self):
        status, result = self.exercise({}, exit_code=2)
        self.assertEqual(1, status)
        self.assertFalse(result['passed'])
        self.assertIn('Agent exited 2', result['errors'][0])


if __name__ == '__main__':
    unittest.main()
