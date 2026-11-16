import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from vm_tools import start_vm


class SetupTests(unittest.TestCase):
    def test_disk_json_formats(self):
        for text in ('[{"name":"agentvm-persist"}]', '{"name":"other"}\n{"name":"agentvm-persist"}\n'):
            self.assertEqual(start_vm.records(text)[-1]['name'], 'agentvm-persist')
        with self.assertRaises(ValueError):
            start_vm.records('invalid')

    def run_setup(self, action='setup', existing=False, disk=False, invalid=False):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            if command[1] == 'validate' and invalid:
                raise subprocess.CalledProcessError(1, command)
            if command[1:] == ['list', '--json']:
                return subprocess.CompletedProcess(command, 0, '[{"name":"agentvm"}]' if existing else '[]')
            if command[1:] == ['disk', 'list', '--json']:
                return subprocess.CompletedProcess(command, 0, '[{"name":"agentvm-persist"}]' if disk else '[]')
            return subprocess.CompletedProcess(command, 0)
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / 'db-source'
            (db / 'scripts').mkdir(parents=True)
            for name in ('compose.yaml', 'Dockerfile', 'scripts/configure.py', 'scripts/create-db.sh', 'scripts/setup.sh'):
                (db / name).touch()
            source = Path(directory) / 'mountavm.yaml'
            with patch('vm_tools.mounts.DEFAULT_DATABASE_SOURCE', db), \
                 patch.object(sys, 'argv', ['start_vm', action, str(source)]), \
                 patch.object(start_vm.subprocess, 'run', side_effect=run), \
                 contextlib.redirect_stderr(io.StringIO()):
                if invalid or (action == 'recreate' and existing and not disk):
                    with self.assertRaises(SystemExit):
                        start_vm.main()
                else:
                    start_vm.main()
            self.assertEqual(set(Path(directory).iterdir()), {db})
        return calls

    def test_fresh_setup_creates_disk_and_vm(self):
        calls = self.run_setup()
        self.assertIn(['limactl', 'disk', 'create', 'agentvm-persist', '--size', '20GiB'], calls)
        self.assertTrue(any('--name=agentvm' in c and '--timeout=30m' in c for c in calls))

    def test_rerun_reuses_disk_and_instance(self):
        calls = self.run_setup(existing=True, disk=True)
        self.assertIn(['limactl', 'start', '--tty=false', '--timeout=30m', 'agentvm'], calls)
        self.assertTrue(any(c[1] == 'shell' for c in calls))
        self.assertFalse(any(c[1:3] in (['disk', 'create'], ['delete', '--force']) for c in calls))

    def test_missing_disk_prevents_destructive_recreation(self):
        calls = self.run_setup('recreate', existing=True)
        self.assertFalse(any(c[1] == 'delete' for c in calls))

    def test_legacy_disk_prevents_new_disk_creation(self):
        with patch.object(start_vm, 'lima_records', return_value=[{'name': 'agentvm-db'}]), \
             patch.object(start_vm.subprocess, 'run') as run, \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                start_vm.ensure_disk()
            run.assert_not_called()

    def test_legacy_disk_blocks_even_if_new_disk_exists(self):
        with patch.object(start_vm, 'lima_records', return_value=[{'name': 'agentvm-db'}, {'name': 'agentvm-persist'}]), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                start_vm.ensure_disk(required=True)

    def test_validation_failure_prevents_mutations(self):
        calls = self.run_setup(invalid=True)
        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
