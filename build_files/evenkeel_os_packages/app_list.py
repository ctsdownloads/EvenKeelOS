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


def remember(entry):
    records = [r for r in load() if not (r["package"] == entry["package"] and r["where"] == entry["where"])]
    save(records + [entry])


def forget(entry):
    save([r for r in load() if not (r["package"] == entry["package"] and r["where"] == entry["where"])])
