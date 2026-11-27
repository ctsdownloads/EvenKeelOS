"""The record of what was installed, for Remove Apps."""
import json
from evenkeel_os_packages import common


def load():
    try:
        return json.loads(common.STATE.read_text())
    except (OSError, ValueError):
        return []


def save(records):
    common.STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = common.STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(records, indent=1))
    tmp.replace(common.STATE)


def others(entry):
    return [r for r in load() if (r["package"], r["where"]) != (entry["package"], entry["where"])]


def remember(entry):
    save(others(entry) + [entry])


def forget(entry):
    save(others(entry))
