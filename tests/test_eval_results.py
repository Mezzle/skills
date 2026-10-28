import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from eval_results import saved_results


class ResultsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def record(self, run, case, passed=True, repetition=1, order=1, **settings):
        path = self.root / run / f'{case}-{repetition}' / 'result.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        result = {'case': case, 'passed': passed, 'errors': [] if passed else ['Failed check'],
                  'repetition': repetition, 'provider': 'claude', 'requested_model': 'opus',
                  'requested_effort': 'high', 'claude_allow_unix_sockets': True,
                  'skill_sha256': 'current', **settings}
        path.write_text(json.dumps(result))
        os.utime(path, (order, order))
        return path

    def report(self, **kwargs):
        return saved_results(self.root, ['first', 'second'], 'current', **kwargs)

    def test_combines_cases_from_separate_batches(self):
        self.record('batch-a', 'first')
        self.record('batch-b', 'second', order=2)
        self.assertEqual('PASS', self.report()['providers'][0]['status'])

    def test_new_failure_overrides_earlier_success(self):
        self.record('old', 'first')
        self.record('old', 'second')
        self.record('new', 'first', passed=False, order=2)
        report = self.report(history=True)
        self.assertEqual('FAIL', report['providers'][0]['cases'][0]['status'])
        self.assertEqual(3, len(report['history']))

    def test_missing_cases_are_not_a_pass(self):
        self.record('run', 'first')
        self.assertEqual('NOT RUN', self.report()['providers'][0]['cases'][1]['status'])
        self.assertNotEqual('PASS', self.report()['providers'][0]['status'])

    def test_settings_are_not_mixed(self):
        self.record('old', 'first', claude_allow_unix_sockets=False)
        self.record('new', 'second', order=2)
        self.assertEqual('NOT RUN', self.report()['providers'][0]['cases'][0]['status'])

    def test_changed_skill_marks_results_stale(self):
        self.record('run', 'first', skill_sha256='old')
        self.record('run', 'second', skill_sha256='old')
        report = self.report()['providers'][0]
        self.assertTrue(report['stale'])
        self.assertNotEqual('PASS', report['status'])

    def test_missing_repetitions_report_incomplete(self):
        self.record('run', 'first', planned_repetitions=3)
        self.assertEqual('INCOMPLETE', self.report()['providers'][0]['cases'][0]['status'])

    def test_old_repetitions_do_not_fill_new_attempt(self):
        self.record('old', 'first', repetition=1, planned_repetitions=2)
        self.record('old', 'first', repetition=2, planned_repetitions=2)
        self.record('new', 'first', repetition=1, planned_repetitions=2, order=2)
        case = self.report()['providers'][0]['cases'][0]
        self.assertEqual('INCOMPLETE', case['status'])
        self.assertEqual(1, case['total'])

    def test_malformed_artifact_is_reported(self):
        path = self.record('run', 'first')
        path.write_text('{')
        self.assertEqual(1, len(self.report()['invalid_artifacts']))

    def test_legacy_result_without_provider_is_codex(self):
        path = self.record('run', 'first')
        data = json.loads(path.read_text())
        data.pop('provider')
        path.write_text(json.dumps(data))
        self.assertEqual('codex', self.report()['providers'][0]['provider'])

    def test_council_blockers_remain_visible(self):
        path = self.root / 'council-run' / 'summary.json'
        path.parent.mkdir()
        path.write_text(json.dumps({'passed': False, 'members': [{'blocker': 'Third maker unavailable'}]}))
        self.assertEqual(['Third maker unavailable'], self.report()['council']['blockers'])


if __name__ == '__main__':
    unittest.main()
