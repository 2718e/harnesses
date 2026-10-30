#!/usr/bin/env python3
"""Replace a stopped Lima instance's mounts with the complete desired list.

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
    if not isinstance(raw_mounts, list):
        fail("mounts must be a list")

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

        location = os.path.expanduser(location)
        if not os.path.isabs(location):
            fail(f"location is not absolute: {location}")
        location = os.path.realpath(location)
        mount_point = os.path.normpath(mount_point)

        if not os.path.isabs(location):
            fail(f"location is not absolute: {location}")
        if not os.path.isabs(mount_point):
            fail(f"mountPoint is not absolute: {mount_point}")
        if not os.path.exists(location):
            fail(f"location does not exist on the host: {location}")

        normalized = dict(raw)
        normalized.update(location=location, mountPoint=mount_point, writable=writable)
        # Accept the old local config entry only if it exactly repeats the
        # required mount. This lets existing mountavm.yaml files keep working.
        if normalized in mounts and mount_point == "/opt/agent-config":
            continue
        mounts.append(normalized)

    for index, mount in enumerate(mounts):
        for other in mounts[index + 1:]:
            if mount["mountPoint"] == other["mountPoint"]:
                fail(f"duplicate mountPoint: {mount['mountPoint']}")
            for key in ("mountPoint", "location"):
                if is_ancestor(mount[key], other[key]) or is_ancestor(other[key], mount[key]):
                    fail(f"overlapping {key}: {mount[key]} and {other[key]}")

    return mounts


def desired_configuration(source):
    """Resolve the tracked required mounts and host-specific mount list."""
    source_data = load_yaml(source)
    if not isinstance(source_data, dict):
        fail("source is not a mapping")
    base_path = Path(__file__).resolve().parent.parent / "agentvm.yaml"
    bases = source_data.get("base")
    if bases != ["./agentvm.yaml"]:
        fail("mountavm.yaml must use only ./agentvm.yaml as its base")
    base_data = load_yaml(base_path)
    required = base_data.get("mounts", [])
    if not isinstance(required, list):
        fail("base mounts must be a list")
    required = [dict(mount) for mount in required]
    config_dir = str(base_path.parent / "agent-config")
    for mount in required:
        if mount.get("location") == "{{.Param.AgentConfig}}":
            mount["location"] = config_dir
    local_mounts = source_data.get("mounts", [])
    if not isinstance(local_mounts, list):
        fail("local mounts must be a list")
    combined = normalize_mounts(required + local_mounts)
    return source_data, base_path, combined, config_dir


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
    _, _, mounts, _ = desired_configuration(source)

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
