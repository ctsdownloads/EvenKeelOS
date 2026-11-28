"""The record of what was installed, for Remove Apps."""
import json
from evenkeel_os_packages import common
from evenkeel_os_ui import save_json


def load():
    try:
        return json.loads(common.STATE.read_text())
    except (OSError, ValueError):
        return []


def save(records):
    save_json(common.STATE, records)


def others(entry):
    return [r for r in load() if (r["package"], r["where"]) != (entry["package"], entry["where"])]


def remember(entry):
    save(others(entry) + [entry])


def forget(entry):
    save(others(entry))
