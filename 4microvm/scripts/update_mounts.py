#!/usr/bin/env python3
"""Replace a stopped Lima instance's mounts with the mounts from a source template.

The source file is the host-specific mountavm.yaml. The target is the instance
copy at ~/.lima/<name>/lima.yaml; editing mountavm.yaml alone does not affect an
existing VM.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: PyYAML is required (Debian: python3-yaml)", file=sys.stderr)
    raise SystemExit(1)


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except FileNotFoundError:
        fail(f"file not found: {path}")
    except yaml.YAMLError as error:
        fail(f"invalid YAML in {path}: {error}")


def instance_records():
    try:
        result = subprocess.run(
            ["limactl", "list", "--json"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        fail("limactl is not installed or not on PATH")
    except subprocess.CalledProcessError as error:
        fail(f"limactl list --json failed: {error.stderr.strip()}")
    try:
        records = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        fail(f"could not parse limactl output: {error}")
    if isinstance(records, dict):
        records = records.get("instances", [])
    return records


def find_instance(name):
    for record in instance_records():
        if record.get("name") == name:
            return record
    fail(f"Lima instance not found: {name}")


def is_ancestor(parent, child):
    parent = parent.rstrip(os.sep)
    child = child.rstrip(os.sep)
    return child == parent or child.startswith(parent + os.sep)


def normalize_mounts(raw_mounts):
    if not isinstance(raw_mounts, list) or not raw_mounts:
        fail("source has no mounts")

    mounts = []
    for index, raw in enumerate(raw_mounts):
        if not isinstance(raw, dict):
            fail(f"mount #{index + 1} is not a mapping")

        location = raw.get("location")
        mount_point = raw.get("mountPoint")
        writable = raw.get("writable", False)

        if not isinstance(location, str) or not location:
            fail(f"mount #{index + 1} has no location")
        if not isinstance(mount_point, str) or not mount_point:
            fail(f"mount #{index + 1} has no mountPoint")
        if not isinstance(writable, bool):
            fail(f"mount #{index + 1} has a non-boolean writable")

        location = os.path.normpath(os.path.expanduser(location))
        mount_point = os.path.normpath(mount_point)

        if not os.path.isabs(location):
            fail(f"location is not absolute: {location}")
        if not os.path.isabs(mount_point):
            fail(f"mountPoint is not absolute: {mount_point}")
        if not os.path.exists(location):
            fail(f"location does not exist on the host: {location}")

        mounts.append(
            {
                "location": location,
                "mountPoint": mount_point,
                "writable": writable,
            }
        )

    for index, mount in enumerate(mounts):
        for other in mounts[index + 1:]:
            if mount["mountPoint"] == other["mountPoint"]:
                fail(f"duplicate mountPoint: {mount['mountPoint']}")
            for key in ("mountPoint", "location"):
                if is_ancestor(mount[key], other[key]) or is_ancestor(other[key], mount[key]):
                    fail(f"overlapping {key}: {mount[key]} and {other[key]}")

    return mounts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("instance", help="Lima instance name")
    parser.add_argument("source", help="mountavm.yaml path")
    args = parser.parse_args()

    record = find_instance(args.instance)
    status = str(record.get("status", "")).lower()
    if "running" in status:
        fail(f"instance {args.instance} is running; stop it before updating mounts")

    instance_dir = record.get("dir")
    if not instance_dir:
        lima_home = os.environ.get("LIMA_HOME", os.path.expanduser("~/.lima"))
        instance_dir = os.path.join(lima_home, args.instance)
    target = Path(instance_dir) / "lima.yaml"
    if not target.exists():
        fail(f"instance YAML not found: {target}")

    source = Path(args.source).expanduser()
    source_data = load_yaml(source)
    if not isinstance(source_data, dict):
        fail(f"source is not a mapping: {source}")
    mounts = normalize_mounts(source_data.get("mounts"))

    target_data = load_yaml(target)
    if not isinstance(target_data, dict):
        fail(f"instance YAML is not a mapping: {target}")

    target_data["mounts"] = mounts
    temporary = target.with_name(target.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(target_data, handle, sort_keys=False)
        temporary.chmod(target.stat().st_mode & 0o777)
        os.replace(temporary, target)
    except OSError as error:
        fail(f"could not write {target}: {error}")

    print(f"updated {target} with {len(mounts)} mounts")


if __name__ == "__main__":
    main()
