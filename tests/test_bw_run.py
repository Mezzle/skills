"""bw-run against stub bw, security and osascript: no vault, Keychain or dialog."""

import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

BW_RUN = Path(__file__).parents[1] / 'skills/engineering/secrets/scripts/bw-run'

STUBS = {
    # Valid session is GOODKEY; unlock succeeds when the fd-3 password matches STUB_PW.
    'bw': r'''
        echo "bw $*" >> "$STUB/log"
        args=" $* "
        if [[ $args == *" status "* ]]; then echo "{\"status\":\"${STUB_STATUS:-locked}\"}"; exit 0; fi
        if [[ $args == *" unlock "* && $args == *"--check"* ]]; then [ "${BW_SESSION:-}" = GOODKEY ]; exit; fi
        if [[ $args == *" unlock "* ]]; then
          [ "$(head -n1 /dev/fd/3)" = "$STUB_PW" ] && { printf GOODKEY; exit 0; }
          echo "Invalid master password." >&2; exit 1
        fi
        [ "${BW_SESSION:-}" = GOODKEY ] && echo "RAN $*" || { echo locked >&2; exit 1; }
    ''',
    'security': r'''
        if [ "$1" = -i ]; then sed 's/.* -w //' > "$STUB/kc"; exit 0; fi
        [ -f "$STUB/kc" ] && cat "$STUB/kc" || exit 44
    ''',
    'osascript': r'''
        cat > /dev/null; echo dialog >> "$STUB/log"; sleep "${STUB_SLEEP:-0}"
        case "$STUB_PIN" in
          CANCEL) echo "User canceled. (-128)" >&2; exit 1 ;;
          TIMEOUT) echo TIMEOUT ;;
          *) echo "OK:$STUB_PIN" ;;
        esac
    ''',
}


class BwRunTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.stub = Path(temporary.name)
        bin_dir = self.stub / 'bin'
        bin_dir.mkdir()
        for name, body in STUBS.items():
            path = bin_dir / name
            path.write_text('#!/usr/bin/env bash\n' + textwrap.dedent(body))
            path.chmod(0o755)
        self.env = {**os.environ, 'PATH': f'{bin_dir}:{os.environ["PATH"]}', 'STUB': str(self.stub),
                    'TMPDIR': str(self.stub), 'STUB_PW': ' p%a ss+&', 'STUB_PIN': ' p%a ss+&'}

    def run_bw(self, *args, **env):
        return subprocess.run([str(BW_RUN), *args], env={**self.env, **env},
                              capture_output=True, text=True, timeout=30)

    def dialogs(self):
        log = self.stub / 'log'
        return log.read_text().count('dialog') if log.exists() else 0

    def test_unlocks_once_then_reuses_the_cached_session(self):
        first = self.run_bw('get', 'password', 'item')
        second = self.run_bw('get', 'password', 'item')
        self.assertEqual(first.stdout, 'RAN --nointeraction get password item\n')
        self.assertEqual(second.returncode, 0)
        self.assertEqual(self.dialogs(), 1)
        self.assertNotIn('GOODKEY', first.stdout + first.stderr + (self.stub / 'log').read_text())

    def test_expired_cache_asks_again(self):
        (self.stub / 'kc').write_text('0:GOODKEY\n')
        self.assertEqual(self.run_bw('list', 'folders').returncode, 0)
        self.assertEqual(self.dialogs(), 1)

    def test_parallel_runs_share_one_dialog(self):
        env = {**self.env, 'STUB_SLEEP': '2'}
        runs = [subprocess.Popen([str(BW_RUN), 'get', 'password', str(n)], env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for n in range(3)]
        self.assertEqual([run.wait(timeout=30) for run in runs], [0, 0, 0])
        self.assertEqual(self.dialogs(), 1)

    def test_failures_name_the_cause(self):
        cases = {
            'the password dialog was cancelled.': {'STUB_PIN': 'CANCEL'},
            'the password dialog timed out.': {'STUB_PIN': 'TIMEOUT'},
            'no password entered.': {'STUB_PIN': ''},
            'bw unlock failed: Invalid master password.': {'STUB_PIN': 'wrong'},
            'signed out': {'STUB_STATUS': 'unauthenticated'},
        }
        for message, env in cases.items():
            with self.subTest(message):
                (self.stub / 'kc').unlink(missing_ok=True)
                result = self.run_bw('get', 'password', 'item', **env)
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)

    def test_refuses_commands_that_expose_or_end_the_session(self):
        for args in (['unlock', '--raw'], ['--quiet', 'logout'], ['serve'],
                     ['get', 'password', 'x', '--session=y']):
            with self.subTest(args):
                result = self.run_bw(*args)
                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stderr.startswith('bw-run: refusing'))
        self.assertEqual(self.dialogs(), 0)


if __name__ == '__main__':
    unittest.main()
