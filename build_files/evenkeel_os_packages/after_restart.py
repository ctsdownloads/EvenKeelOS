"""Work left for the first login after a restart."""
import json

from evenkeel_os_ui import ask, notify, say
from evenkeel_os_packages import boxes, common, installed, launchers, login_apps, printers, targets


PENDING = common.STATE.with_name("pending.json")


def pending():
    try:
        return json.loads(PENDING.read_text())
    except (OSError, ValueError):
        return []


def save_pending(entries):
    PENDING.parent.mkdir(parents=True, exist_ok=True)
    if entries:
        PENDING.write_text(json.dumps(entries, indent=1))
    else:
        PENDING.unlink(missing_ok=True)


def boxes_missing_helpers():
    return [k for k in common.BOXES if boxes.box_exists(common.BOXES[k]["name"]) and not boxes.helpers_mark(k).exists()]


def after_restart():
    """At login: give old boxes the desktop helpers, then report packages added to the system, once."""
    for k in boxes_missing_helpers():
        boxes.ensure_helpers(k, quiet=True)
    for f, box in launchers.launchers_to_fix():      # app grid entries made by an older Install Package File
        launchers.fix_launcher(f, box)
    login_apps.fix_app_login_files()
    left = []
    for e in pending():
        have = installed.host_version(e["package"])
        if have and (not e.get("version") or have == e["version"]):
            if e.get("printer"):
                notify(f"The printer driver {e['title']} is ready.")
                if ask(f"The printer driver {e['title']} is ready.\n\nOpen Printers: choose Add Printer, then "
                       f"your printer.", ok="Open Printers", cancel="Later") == "ok":
                    printers.open_printers()
            else:
                notify(f"{e['title']} is ready.")
                say(f"{e['title']} is ready. Find it in Show Apps.")
        elif targets.staged_system():
            left.append(e)          # added, but this computer has not restarted into it yet
        else:
            notify(f"{e['title']} did not get installed.")
            say(f"{e['title']} did not get installed. The computer may have started an older version of the system. "
                f"Open the file again to install it.", "warning")
    save_pending(left)
    return 0
