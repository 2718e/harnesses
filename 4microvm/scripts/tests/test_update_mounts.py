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
    def test_removes_only_unused_legacy_mount_parameters(self):
        config = {"param": {"AgentConfig": "/config", "SharedDevDB": "/db", "Other": "keep"},
                  "mounts": [], "provision": [{"script": "{{.Param.SharedDevDB}}"}]}
        update_mounts.remove_unused_mount_params(config)
        self.assertEqual(config["param"], {"SharedDevDB": "/db", "Other": "keep"})

    def test_removes_empty_parameter_mapping(self):
        config = {"param": {"AgentConfig": "/config"}, "mounts": []}
        update_mounts.remove_unused_mount_params(config)
        self.assertNotIn("param", config)

    def test_lima_output_formats_find_instances(self):
        examples = [
            '{"name":"agentvm","status":"Stopped"}',
            '[{"name":"agentvm","status":"Stopped"}]',
            '{"name":"other"}\n{"name":"agentvm","status":"Stopped"}\n',
        ]
        for output in examples:
            with self.subTest(output=output), patch.object(
                update_mounts.subprocess, "run",
                return_value=subprocess.CompletedProcess([], 0, stdout=output),
            ):
                self.assertEqual(update_mounts.find_instance("agentvm")["status"], "Stopped")

    def test_invalid_lima_output_reports_error(self):
        with patch.object(update_mounts.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout="bad json")), \
             contextlib.redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit):
                update_mounts.instance_records()
            self.assertIn("could not parse limactl output", errors.getvalue())

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
                self.assertRegex(Path(validate.call_args.args[0][2]).stem,
                                 r'^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$')
            self.assertEqual(list(Path(directory).glob("*.yaml")), [target])

    def test_validation_failure_preserves_configuration(self):
        self.run_update(True)

    def test_validation_success_replaces_configuration(self):
        self.run_update(False)
