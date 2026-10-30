#!/usr/bin/env python3
"""Resolve the required mount before creating a Lima instance."""
import argparse
import os
import subprocess
import tempfile
from pathlib import Path

import yaml
from update_mounts import desired_configuration, fail


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("create", "recreate"))
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    data, _, mounts, config_dir = desired_configuration(source)
    params = data.setdefault("param", {})
    if not isinstance(params, dict):
        fail("param must be a mapping")
    params["AgentConfig"] = config_dir
    # Lima merges the required mount from the base; retain all other validated
    # local mounts, including options, and remove the legacy duplicate.
    data["mounts"] = [m for m in mounts if m["mountPoint"] != "/opt/agent-config"]

    # Place the temporary template next to the source so relative base and
    # provisioning file references keep their normal meaning.
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".yaml", dir=source.parent, delete=False) as handle:
            temp_path = handle.name
            yaml.safe_dump(data, handle, sort_keys=False)
        subprocess.run(["limactl", "validate", temp_path], check=True)
        if args.action == "recreate":
            subprocess.run(["limactl", "delete", "--force", "agentvm"], check=True)
        subprocess.run(["limactl", "start", "--name=agentvm", temp_path], check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        fail(f"could not {args.action} agentvm: {error}")
    finally:
        if temp_path:
            os.unlink(temp_path)


if __name__ == "__main__":
    main()
