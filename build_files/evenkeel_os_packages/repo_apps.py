"""Installing an app by name from Fedora's or Ubuntu's own repositories, into its box."""
import subprocess

from evenkeel_os_ui import notify, say
from evenkeel_os_packages import app_list, boxes, common, installed, launchers, update_notes, windows


def package_files(box, kind, name):
    cmd = ["rpm", "-ql", name] if kind == "rpm" else ["dpkg", "-L", name]
    r = subprocess.run(boxes.in_box(box, *cmd), capture_output=True, text=True)
    return r.stdout.split() if r.returncode == 0 else []


def install(kind, name, title):
    """Set up the box if needed, install the package, and put its apps in Show Apps and Remove Apps."""
    box = common.BOXES[kind]["name"]
    label = common.BOXES[kind]["label"]
    if not boxes.box_exists(box):
        _, size = boxes.first_time(kind)
        if not boxes.room_for(boxes.setup_need(size) + 1000) or not boxes.setup_box(kind, size):
            return 1
    elif not boxes.room_for(1000):
        return 1
    boxes.ensure_helpers(kind)
    if kind == "rpm":
        steps = [(f"Installing {title}", boxes.in_box(box, "sudo", "dnf", "-y", "install", name))]
    else:
        steps = [("Getting Ubuntu's list of packages", boxes.in_box(box, "sudo", "apt-get", "update")),
                 (f"Installing {title}", boxes.in_box(box, "sudo", "env", "DEBIAN_FRONTEND=noninteractive",
                                                     "apt-get", "install", "-y", name))]
    if not windows.run_steps(f"Installing {title} in the {label}.", steps):
        windows.failed(f"Installing {title}")
        return 1
    files = package_files(box, kind, name)
    info = {"apps": [f for f in files if f.startswith("/usr/share/applications/") and f.endswith(".desktop")],
            "bins": [f for f in files if f.startswith("/usr/bin/")]}
    apps, bins = launchers.export(box, info)
    app_list.remember({"title": title, "package": name, "where": box, "apps": apps, "bins": bins,
                       "version": installed.box_version(kind, name), "updates": True})
    notify(f"{title} is installed.")
    where = "Find it in Show Apps." if apps else "It is a command-line tool, so it has no window in Show Apps."
    say(f"{title} is installed in the {label}. {where}\n\n{update_notes.UPDATES_YES}")
    return 0
