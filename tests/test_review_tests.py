import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import review_tests as suite

CASES = {case['id']: case for case in json.loads(
    (suite.ROOT / 'tests/cases/review-loop.json').read_text())}


def finding(line, severity='should', file='invoice.py'):
    return {'id': 'S1', 'severity': severity, 'file': file, 'line': line,
            'claim': 'claim', 'fix': 'fix'}


class GradeTest(unittest.TestCase):
    def test_accepts_planted_bug(self):
        answer = {'verdict': 'CHANGES', 'findings': [finding(14)]}
        self.assertEqual(suite.grade(CASES['bug'], answer), ([], 0))

    def test_rejects_missed_bug(self):
        errors, _ = suite.grade(CASES['bug'], {'verdict': 'APPROVE', 'findings': []})
        self.assertEqual(len(errors), 2)

    def test_rejects_downgraded_severity(self):
        errors, _ = suite.grade(CASES['bug'], {'verdict': 'CHANGES', 'findings': [finding(14, 'nit')]})
        self.assertTrue(any('Missed' in error for error in errors))

    def test_accepts_path_prefix(self):
        answer = {'verdict': 'CHANGES', 'findings': [finding(13, file='./invoice.py')]}
        self.assertEqual(suite.grade(CASES['standards'], answer), ([], 0))

    def test_nit_case_approves(self):
        answer = {'verdict': 'APPROVE', 'findings': [finding(13, 'nit')]}
        self.assertEqual(suite.grade(CASES['smell'], answer), ([], 0))

    def test_nit_case_rejects_changes(self):
        errors, _ = suite.grade(CASES['smell'], {'verdict': 'CHANGES', 'findings': [finding(13, 'nit')]})
        self.assertEqual(errors, ['verdict: expected APPROVE, got CHANGES'])

    def test_counts_false_positive(self):
        answer = {'verdict': 'CHANGES', 'findings': [finding(14), finding(3)]}
        self.assertEqual(suite.grade(CASES['bug'], answer), ([], 1))

    def test_allows_weak_test_finding(self):
        answer = {'verdict': 'CHANGES', 'findings': [finding(14), finding(11, file='test_invoice.py')]}
        self.assertEqual(suite.grade(CASES['bug'], answer), ([], 0))

    def test_clean_rejects_should(self):
        errors, false_positives = suite.grade(CASES['clean'], {'verdict': 'CHANGES', 'findings': [finding(13)]})
        self.assertEqual(false_positives, 1)
        self.assertEqual(len(errors), 2)

    def test_clean_accepts_nit(self):
        answer = {'verdict': 'APPROVE', 'findings': [finding(13, 'nit')]}
        self.assertEqual(suite.grade(CASES['clean'], answer), ([], 0))

    def test_rejects_malformed(self):
        self.assertEqual(suite.grade(CASES['bug'], {'verdict': 'CHANGES'}), (['Malformed result'], 0))


class FixtureTest(unittest.TestCase):
    def test_every_case_has_a_variant(self):
        self.assertEqual(set(CASES), {p.name for p in (suite.FIXTURE / 'variants').iterdir()})

    def test_brief_renders_without_input_placeholders(self):
        brief = suite.render_brief(suite.skill_text(None), Path('/repo'), 'abc')
        self.assertIn('Spec: SPEC.md', brief)
        self.assertFalse(re.search(r'<(abs path|sha|intent|scope|results)>', brief))

    def test_planted_ranges_cover_the_change(self):
        for case in CASES.values():
            with tempfile.TemporaryDirectory() as temporary:
                work = Path(temporary)
                suite.prepare(work, case['id'])
                checks = subprocess.run(['python3', '-m', 'unittest', '-q'], cwd=work,
                                        capture_output=True, text=True)
                self.assertEqual(checks.returncode, 0, case['id'] + checks.stderr)
                lines = (work / 'invoice.py').read_text().splitlines()
                for hit in case['expect']['hits']:
                    self.assertLessEqual(hit['lines'][1], len(lines), case['id'])
                    self.assertTrue(lines[hit['lines'][0] - 1].strip(), case['id'])


if __name__ == '__main__':
    unittest.main()
