import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


VM_ROOT = Path(__file__).resolve().parents[2]


class HarnessConfigTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.home = root / 'home'
        self.source = root / 'config'
        (self.source / 'bin').mkdir(parents=True)
        (self.source / 'codex').mkdir()
        (self.source / 'skills' / 'example').mkdir(parents=True)
        (self.source / 'AGENTS.md').write_text('VM guidance\n')
        (self.source / 'codex' / 'config.toml').write_text('approval_policy = "never"\n')
        (self.source / 'skills' / 'example' / 'SKILL.md').write_text('initial skill\n')
        shutil.copyfile(
            VM_ROOT / 'agent-config' / 'bin' / 'sync-agent-config',
            self.source / 'bin' / 'sync-agent-config',
        )

    def sync(self):
        return subprocess.run(
            ['bash', str(self.source / 'bin' / 'sync-agent-config')],
            env={**os.environ, 'HOME': str(self.home)},
            capture_output=True, text=True, timeout=10,
        )

    def test_sync_is_repeatable_preserves_user_skills_and_links_live_content(self):
        custom = self.home / '.agents' / 'skills' / 'custom' / 'SKILL.md'
        custom.parent.mkdir(parents=True)
        custom.write_text('user skill\n')
        for _ in range(2):
            result = self.sync()
            self.assertEqual(result.returncode, 0, result.stderr)
        installed = self.home / '.agents' / 'skills' / 'example'
        self.assertTrue(installed.is_symlink())
        self.assertEqual(custom.read_text(), 'user skill\n')
        (self.source / 'skills' / 'example' / 'SKILL.md').write_text('updated skill\n')
        self.assertEqual((installed / 'SKILL.md').read_text(), 'updated skill\n')
        for harness in ('.codex', '.dsh'):
            guidance = self.home / harness / 'AGENTS.md'
            self.assertTrue(guidance.is_symlink())
            self.assertEqual(guidance.read_text(), 'VM guidance\n')
        self.assertEqual(
            (self.home / '.codex' / 'config.toml').read_text(),
            (self.source / 'codex' / 'config.toml').read_text(),
        )

    def test_sync_refuses_to_replace_a_local_bundle(self):
        local = self.home / '.agents' / 'skills' / 'example' / 'SKILL.md'
        local.parent.mkdir(parents=True)
        local.write_text('local work\n')
        result = self.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Refusing to replace', result.stderr)
        self.assertEqual(local.read_text(), 'local work\n')


@unittest.skipUnless(shutil.which('just'), 'just is required')
class NukeConfirmationTests(unittest.TestCase):
    def invoke(self, answer):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            calls = root / 'calls'
            fake_lima = root / 'limactl'
            fake_lima.write_text(
                '#!/bin/sh\n'
                'printf "%s\\n" "$*" >> "$TEST_LIMA_CALLS"\n'
            )
            fake_lima.chmod(0o755)
            environment = {
                **os.environ,
                'PATH': str(root) + os.pathsep + os.environ.get('PATH', ''),
                'TEST_LIMA_CALLS': str(calls),
            }
            # Environment settings must not bypass the confirmation being tested.
            for name in ('JUST_YES', 'JUST_DRY_RUN', 'JUST_JUSTFILE', 'JUST_WORKING_DIRECTORY'):
                environment.pop(name, None)
            result = subprocess.run(
                ['just', '--justfile', str(VM_ROOT / 'justfile'), 'nuke'],
                input=answer, env=environment, capture_output=True, text=True,
                timeout=10,
            )
            return result, calls.read_text().splitlines() if calls.exists() else []

    def test_decline_or_eof_runs_no_deletion(self):
        for answer in ('n\n', ''):
            with self.subTest(answer=answer):
                result, calls = self.invoke(answer)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, [])

    def test_confirmation_deletes_vm_then_disk(self):
        result, calls = self.invoke('y\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['delete --force agentvm', 'disk delete agentvm-db'])


if __name__ == '__main__':
    unittest.main()
