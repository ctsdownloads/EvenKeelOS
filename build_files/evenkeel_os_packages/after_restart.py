"""Work left for the first login after a restart."""
import json
import subprocess

from evenkeel_os_ui import _, ask, notify, offer_restart, say
from evenkeel_os_packages import (boxes, common, installed, launchers, login_apps, printers, targets, update_notes,
                                  vpn)


PENDING = common.STATE.with_name("pending.json")


def offer(title, rest):
    """Say a package added to the system is in, and offer the restart that starts it; rest: what comes after."""
    notify(_("{title} is installed. Restart to use it.").format(title=title))
    offer_restart(_("{title} is installed. Restart to start using it.").format(title=title), rest)


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


def without(package):
    return [e for e in pending() if e["package"] != package]


def drop_pending(package):
    save_pending(without(package))


def add_pending(entry):
    """Check this package at the next login, in place of any earlier entry for it."""
    save_pending(without(entry["package"]) + [entry])


def where_line(package):
    """Where to find a package added to the system, from the files it installed."""
    r = subprocess.run(["rpm", "-ql", package], capture_output=True, text=True)
    files = r.stdout.splitlines() if r.returncode == 0 else []
    return update_notes.where_to_find(
        any(f.startswith("/usr/share/applications/") and f.endswith(".desktop") for f in files),
        any(f.startswith(("/usr/bin/", "/usr/sbin/")) for f in files), _("It has no window of its own in Show Apps."))


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
            if e.get("vpn"):
                if not vpn.turn_on(e):
                    left.append(e)      # asked again at the next login
                continue
            if e.get("services") and not vpn.turn_on_services(e):
                left.append(e)
                continue
            if e.get("printer"):
                notify(_("The printer driver {title} is ready.").format(title=e["title"]))
                if ask(_("The printer driver {title} is ready.\n\nOpen Printers: choose Add Printer, then your "
                         "printer.").format(title=e["title"]), ok=_("Open Printers"), cancel=_("Later")) == "ok":
                    printers.open_printers()
            else:
                notify(_("{title} is ready.").format(title=e["title"]))
                say(_("{title} is ready.").format(title=e["title"]) + " " + where_line(e["package"]))
        elif targets.staged_system():
            left.append(e)          # added, but this computer has not restarted into it yet
        else:
            again = _("Pick it again in Get a VPN.") if e.get("vpn") else _("Open the file again to install it.")
            notify(_("{title} did not get installed.").format(title=e["title"]))
            say(_("{title} did not get installed. The computer may have started an older version of the system.")
                .format(title=e["title"]) + " " + again, "warning")
    save_pending(left)
    return 0
