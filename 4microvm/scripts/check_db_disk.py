#!/usr/bin/env python3
"""Fail closed if Lima's JSON disk list does not contain the persistent disk."""
import json
import sys

try:
    text = sys.stdin.read()
    decoder = json.JSONDecoder()
    records = []
    while text.strip():
        text = text.lstrip()
        value, end = decoder.raw_decode(text)
        records.extend(value if isinstance(value, list) else [value])
        text = text[end:]
    if not any(isinstance(item, dict) and item.get("name") == "pgdata" for item in records):
        raise ValueError("pgdata disk not found")
except (ValueError, json.JSONDecodeError) as exc:
    sys.exit(f"Cannot recreate VM safely: {exc}. Check `limactl disk list` first.")
