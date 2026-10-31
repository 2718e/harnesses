#!/usr/bin/env python3
"""Resolve the required mount before creating a Lima instance."""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

import yaml
from .mounts import desired_configuration, fail


def records(output):
    """Accept both JSON arrays and Lima versions emitting one object per line."""
    decoder = json.JSONDecoder()
    result = []
    while output.strip():
        value, end = decoder.raw_decode(output.lstrip())
        result.extend(value if isinstance(value, list) else [value])
        output = output.lstrip()[end:]
    if any(not isinstance(item, dict) for item in result):
        raise ValueError("expected Lima JSON objects")
    return result


def lima_records(*arguments):
    result = subprocess.run(["limactl", *arguments, "--json"], check=True, capture_output=True, text=True)
    return records(result.stdout)


def ensure_disk(*, required=False):
    if any(disk.get("name") == "agentvm-db" for disk in lima_records("disk", "list")):
        return
    if required:
        fail("agentvm-db disk missing; refusing to replace an existing VM's persistent disk")
    subprocess.run(["limactl", "disk", "create", "agentvm-db", "--size", "20GiB"], check=True)


def configure_database():
    subprocess.run(["limactl", "shell", "agentvm", "bash", "/opt/agent-config/bin/setup-shared-dev-db"], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("setup", "create", "recreate"))
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    data, _, mounts, config_dir = desired_configuration(source)
    params = data.setdefault("param", {})
    if not isinstance(params, dict):
        fail("param must be a mapping")
    params["AgentConfig"] = config_dir
    db_mount = next(m for m in mounts if m["mountPoint"] == "/projects/shared-dev-db")
    db_source = Path(db_mount["location"])
    for runtime_file in ("compose.yaml", "scripts/configure.py", "scripts/create-db.sh", "scripts/setup.sh"):
        if not (db_source / runtime_file).is_file():
            fail(f"missing {db_source / runtime_file}; use the current shared-dev-db checkout")
    params["SharedDevDB"] = str(db_source)
    # Lima merges the required mount from the base; retain all other validated
    # local mounts, including options, and remove the legacy duplicate.
    data["mounts"] = [m for m in mounts if m["mountPoint"] not in ("/opt/agent-config", "/projects/shared-dev-db")]

    # Place the temporary template next to the source so relative base and
    # provisioning file references keep their normal meaning.
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".yaml", dir=source.parent, delete=False) as handle:
            temp_path = handle.name
            yaml.safe_dump(data, handle, sort_keys=False)
        subprocess.run(["limactl", "validate", temp_path], check=True)
        existing = any(instance.get("name") == "agentvm" for instance in lima_records("list"))
        ensure_disk(required=existing)
        if existing and args.action != "recreate":
            subprocess.run(["limactl", "start", "--tty=false", "agentvm"], check=True)
            configure_database()
            return
        if existing and args.action == "recreate":
            subprocess.run(["limactl", "delete", "--force", "agentvm"], check=True)
        subprocess.run(["limactl", "start", "--tty=false", "--name=agentvm", temp_path], check=True)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        fail(f"could not {args.action} agentvm: {error}")
    finally:
        if temp_path:
            os.unlink(temp_path)


if __name__ == "__main__":
    main()
