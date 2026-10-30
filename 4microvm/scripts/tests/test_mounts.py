#!/usr/bin/env python3
"""Checks for required/local mount merging without a running Lima VM."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import yaml
from vm_tools.mounts import desired_configuration


class MountMergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "mounts.yaml"
        self.config = Path(__file__).resolve().parents[2] / "agent-config"

    def resolve(self, mounts):
        self.source.write_text(yaml.safe_dump({"base": ["./agentvm.yaml"], "mounts": mounts}))
        return desired_configuration(self.source)[2]

    def test_required_mount_is_added_and_legacy_duplicate_removed(self):
        legacy = {"location": str(self.config), "mountPoint": "/opt/agent-config", "writable": False}
        mounts = self.resolve([legacy])
        self.assertEqual(mounts, [legacy])

    def test_overlapping_source_is_rejected(self):
        parent = {"location": str(self.config.parent), "mountPoint": "/projects/harness", "writable": True}
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.resolve([parent])

    def test_conflicting_required_mount_is_rejected(self):
        conflict = {"location": str(self.config), "mountPoint": "/opt/agent-config", "writable": True}
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.resolve([conflict])


if __name__ == "__main__":
    unittest.main()
