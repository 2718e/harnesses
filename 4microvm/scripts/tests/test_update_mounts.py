import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from vm_tools import update_mounts


class UpdateMountTests(unittest.TestCase):
    def run_update(self, validation_fails):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "lima.yaml"
            original = "mounts: []\n"
            target.write_text(original)
            mounts = [{"location": "/tmp", "mountPoint": "/data", "writable": False}]
            record = {"name": "agentvm", "status": "Stopped", "dir": directory}
            outcome = subprocess.CalledProcessError(1, "limactl validate") if validation_fails else None
            with patch.object(sys, "argv", ["update_mounts", "agentvm", "mountavm.yaml"]), \
                 patch.object(update_mounts, "find_instance", return_value=record), \
                 patch.object(update_mounts, "desired_configuration", return_value=(None, None, mounts, None)), \
                 patch.object(update_mounts.subprocess, "run", side_effect=outcome) as validate, \
                 contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                if validation_fails:
                    with self.assertRaises(SystemExit):
                        update_mounts.main()
                    self.assertEqual(target.read_text(), original)
                else:
                    update_mounts.main()
                    self.assertEqual(yaml.safe_load(target.read_text())["mounts"], mounts)
                self.assertEqual(validate.call_args.args[0][:2], ["limactl", "validate"])
            self.assertEqual(list(Path(directory).glob("*.yaml")), [target])

    def test_validation_failure_preserves_configuration(self):
        self.run_update(True)

    def test_validation_success_replaces_configuration(self):
        self.run_update(False)
