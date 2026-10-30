import os
import sys
from pathlib import Path

import yaml


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
    base_path = Path(__file__).resolve().parents[2] / "agentvm.yaml"
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


