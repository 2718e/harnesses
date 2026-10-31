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
import tempfile
from pathlib import Path

import yaml
from .mounts import desired_configuration, fail, load_yaml


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
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".yaml", dir=target.parent, delete=False) as handle:
            temporary = Path(handle.name)
            yaml.safe_dump(target_data, handle, sort_keys=False)
        temporary.chmod(target.stat().st_mode & 0o777)
        subprocess.run(["limactl", "validate", str(temporary)], check=True)
        os.replace(temporary, target)
        temporary = None
    except subprocess.CalledProcessError as error:
        fail(f"Lima rejected the proposed configuration; {target} was not changed: {error}")
    except OSError as error:
        fail(f"could not validate or write {target}: {error}")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    print(f"updated {target} with {len(mounts)} mounts")


if __name__ == "__main__":
    main()
