"""Command line, locking, and the entry point."""
import fcntl
import html
import json
import subprocess
import sys
import time

import evenkeel_os_ui as ui
from evenkeel_os_ui import GUI
from evenkeel_os_packages import (
    after_restart, boxes, common, install_file, launchers, login_apps, reading, remove_apps, windows,
)


def check(path):
    pkg = reading.read_package(path)
    info = reading.classify(pkg)
    print(json.dumps({"kind": pkg.kind, "name": pkg.name, "version": pkg.version, "title": info["title"],
                      "apps": list(info["apps"]), "bins": info["bins"], "rules": list(info["safe_rules"]),
                      "rules_only": info["rules_only"], "source_only": info["source_only"], "needs_root": info["needs_root"],
                      "sources": [n for _, n, on in info["sources"] if on], "needs_system": info["blocking"],
                      "wont_work_in_box": info["notes"]}, indent=1))
    return 0

USAGE = """  evenkeel-os-packages install [FILE]   install an .rpm or .deb (no FILE: pick one from Downloads)
  evenkeel-os-packages remove           remove an app installed this way
  evenkeel-os-packages check FILE       say what a package needs, without installing anything
  evenkeel-os-packages repair           set a broken app box up again (--if-broken: only if one does not work)
  evenkeel-os-packages login            choose box apps that start when you log in"""



def try_lock(lock):
    """Take the lock if it's free; False while another run holds it."""
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False


def take_lock(lock, quiet=False):
    """One install, removal or repair at a time: wait for another (with Cancel). True to go on."""
    if try_lock(lock):
        return True
    if quiet:           # the login task: leave it for the next login rather than wait in the background
        return False
    if not GUI:
        print(f"Waiting for the other install or removal to finish ({doing_now()}).")
        fcntl.flock(lock, fcntl.LOCK_EX)
        return True
    text = waiting_text(doing_now())
    bar = subprocess.Popen(["zenity", f"--title={ui.TITLE}", "--width=520", "--progress", "--pulsate", "--auto-close",
                            f"--text={html.escape(text)}"], stdin=subprocess.PIPE, text=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shown = None
    while True:
        got = try_lock(lock)
        if got or bar.poll() is not None:
            break
        now = doing_now()
        if now != shown:
            shown = now
            ui.feed(bar, "# " + html.escape(waiting_text(now)))
        time.sleep(1)
    ui.finish(bar)
    return got


def waiting_text(now):
    """One line: a progress window's text update ends at the line's end, so a second line would be dropped."""
    return f"Another install or removal is running ({now.rstrip('.')}). This waits for it to finish, then goes on."


def doing_now():
    try:
        return windows.BUSY.read_text().strip() or "Install Package File"
    except OSError:
        return "Install Package File"


def main(argv):
    if len(argv) < 2 or argv[1] not in ("install", "remove", "check", "after-restart", "repair", "login") or \
            (argv[1] == "check" and len(argv) < 3):
        print(USAGE)
        return 2
    if argv[1] == "check":
        return check(argv[2])
    if argv[1] == "after-restart" and not after_restart.pending() and not after_restart.boxes_missing_helpers() and not launchers.launchers_to_fix() \
            and not login_apps.app_login_files_to_fix():
        return 0
    # each window carries the name of what it is part of
    ui.TITLE = {"remove": "Remove Apps", "repair": "Repair App Boxes", "login": "Start Apps at Login"}.get(argv[1], ui.TITLE)
    common.CACHE.mkdir(parents=True, exist_ok=True)
    lock = open(common.CACHE / ".lock", "w")
    if not take_lock(lock, quiet=argv[1] == "after-restart"):
        return 1
    windows.mark_busy({"install": "Install Package File is open", "remove": "Remove Apps is open",
          "repair": "Repair App Boxes is open", "login": "Start Apps at Login is open"}.get(argv[1], "Starting"))
    if argv[1] == "after-restart":
        return after_restart.after_restart()
    if argv[1] == "repair":
        return boxes.repair_command(only_broken="--if-broken" in argv)
    if argv[1] == "install":
        return install_file.install(argv[2] if len(argv) > 2 else None)
    if argv[1] == "login":
        return login_apps.login()
    return remove_apps.remove()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
