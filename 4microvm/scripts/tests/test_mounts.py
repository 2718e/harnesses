#!/usr/bin/env python3
"""Checks for required/local mount merging without a running Lima VM."""
import contextlib
import io
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import yaml
from vm_tools.mounts import desired_configuration


class MountMergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "mounts.yaml"
        self.db_source = Path(self.temp.name) / "db-source"
        self.db_source.mkdir()
        default_source = patch("vm_tools.mounts.DEFAULT_DATABASE_SOURCE", self.db_source)
        default_source.start()
        self.addCleanup(default_source.stop)
        self.config = Path(__file__).resolve().parents[2] / "agent-config"

    def resolve(self, mounts):
        self.source.write_text(yaml.safe_dump({"base": ["./agentvm.yaml"], "mounts": mounts}))
        return desired_configuration(self.source)[2]

    def test_required_mount_is_added_and_legacy_duplicate_removed(self):
        legacy = {"location": str(self.config), "mountPoint": "/opt/agent-config", "writable": False}
        mounts = self.resolve([legacy])
        self.assertEqual(mounts[0], legacy)
        self.assertEqual(mounts[1]["mountPoint"], "/projects/shared-dev-db")

    def test_missing_local_file_uses_default_mounts(self):
        mounts = desired_configuration(self.source)[2]
        self.assertEqual([m["mountPoint"] for m in mounts],
                         ["/opt/agent-config", "/projects/shared-dev-db"])

    def test_db_mount_can_select_another_read_only_checkout(self):
        local = {"location": self.temp.name, "mountPoint": "/projects/shared-dev-db", "writable": False}
        mounts = self.resolve([local])
        self.assertEqual(mounts[1], local)

    def test_writable_db_source_is_rejected(self):
        local = {"location": self.temp.name, "mountPoint": "/projects/shared-dev-db", "writable": True}
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.resolve([local])

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
