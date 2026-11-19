import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / 'agent-config/bin/setup-shared-dev-db'


class GuestDatabaseSetupTests(unittest.TestCase):
    def run_setup(self, *, clone_fails=False, local_source=False, incomplete=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            (source / 'scripts').mkdir(parents=True)
            for name in ('compose.yaml', 'Dockerfile', 'scripts/configure.py',
                         'scripts/create-db.sh', 'scripts/setup.sh'):
                (source / name).write_text(name)
            if incomplete:
                (source / 'scripts/create-db.sh').unlink()
            storage = root / 'storage'
            storage.mkdir()
            tools = root / 'bin'
            tools.mkdir()
            trace = root / 'trace'
            stubs = {
                'mountpoint': 'exit 0',
                'python3': 'printf "configure\\n" >> "$TRACE"',
                'docker': 'printf "build\\n" >> "$TRACE"',
                'systemctl': 'printf "systemctl %s\\n" "$*" >> "$TRACE"',
                'git': ('printf "git %s\\n" "$*" >> "$TRACE"\n'
                        'if [ "${FAIL_CLONE:-}" = 1 ]; then exit 1; fi\n'
                        'for destination; do :; done\n'
                        'cp -R "$FIXTURE" "$destination"'),
            }
            for name, body in stubs.items():
                executable = tools / name
                executable.write_text('#!/bin/sh\nset -eu\n' + body + '\n')
                executable.chmod(0o755)
            script = root / 'setup'
            script.write_text(SCRIPT.read_text().replace(
                'storage=/mnt/lima-agvm-p', 'storage=' + shlex.quote(str(storage))))
            env = dict(os.environ, PATH=f'{tools}:{os.environ["PATH"]}',
                       TRACE=str(trace), FIXTURE=str(source), HOME=str(root),
                       TMPDIR=str(root), FAIL_CLONE='1' if clone_fails else '')
            env.pop('SHARED_DEV_DB_BRANCH', None)
            env.pop('SHARED_DEV_DB_SOURCE', None)
            if local_source:
                env['SHARED_DEV_DB_SOURCE'] = str(source)
            result = subprocess.run(['bash', str(script)], env=env, capture_output=True, text=True)
            log = trace.read_text().splitlines() if trace.exists() else []
            runtime = storage / 'shared-dev-db'
            if clone_fails or incomplete:
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(runtime.exists())
                self.assertFalse(any(line.startswith('systemctl') for line in log))
                return
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((runtime / 'compose.yaml').read_text(), 'compose.yaml')
            self.assertEqual((runtime / 'scripts/create-db.sh').read_text(), 'scripts/create-db.sh')
            self.assertLess(log.index('build'), log.index('systemctl --user stop shared-dev-db.service'))
            self.assertEqual(any(line.startswith('git ') for line in log), not local_source)
            if not local_source:
                self.assertIn('--branch main ', log[0])

    def test_fetches_main_and_snapshots_runtime(self):
        self.run_setup()

    def test_local_source_skips_fetch(self):
        self.run_setup(local_source=True)

    def test_failed_fetch_does_not_stop_service(self):
        self.run_setup(clone_fails=True)

    def test_incomplete_source_does_not_stop_service(self):
        self.run_setup(incomplete=True)
