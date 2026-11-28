"""Installing an app by name from Fedora's or Ubuntu's own repositories, into its box."""
import subprocess

from evenkeel_os_ui import _, notify, say
from evenkeel_os_packages import app_list, boxes, common, installed, launchers, update_notes, windows


def package_files(box, kind, name):
    cmd = ["rpm", "-ql", name] if kind == "rpm" else ["dpkg", "-L", name]
    r = subprocess.run(boxes.in_box(box, *cmd), capture_output=True, text=True)
    return r.stdout.split() if r.returncode == 0 else []


def install(kind, name, title):
    """Set up the box if needed, install the package, and put its apps in Show Apps and Remove Apps."""
    box = common.BOXES[kind]["name"]
    label = _(common.BOXES[kind]["label"])
    if not boxes.box_exists(box):
        size = boxes.first_time(kind)[1]
        if not boxes.room_for(boxes.setup_need(size) + 1000) or not boxes.setup_box(kind, size):
            return 1
    elif not boxes.room_for(1000):
        return 1
    boxes.ensure_helpers(kind)
    if not windows.run_steps(_("Installing {title} in the {label}.").format(title=title, label=label),
                             boxes.install_steps(kind, title, name)):
        windows.failed(_("Installing {title}").format(title=title))
        return 1
    files = package_files(box, kind, name)
    info = {"apps": [f for f in files if f.startswith("/usr/share/applications/") and f.endswith(".desktop")],
            "bins": [f for f in files if f.startswith("/usr/bin/")]}
    apps, bins = launchers.export(box, info)
    app_list.remember({"title": title, "package": name, "where": box, "apps": apps, "bins": bins,
                       "version": installed.box_version(kind, name), "updates": True})
    notify(_("{title} is installed.").format(title=title))
    where = update_notes.where_to_find(apps, True, "")
    say(_("{title} is installed in the {label}.").format(title=title, label=label) + " " + where + "\n\n" +
        update_notes.updates_line(update_notes.UPDATES_FEDORA))
    return 0
