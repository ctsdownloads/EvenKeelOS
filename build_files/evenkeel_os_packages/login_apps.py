"""Box apps that start at login."""
import json
import os
import re
import shlex
import subprocess
from pathlib import Path

from evenkeel_os_ui import choose, say
from evenkeel_os_packages import app_list, boxes, common, launchers, windows


AUTOSTART = common.HOME / ".config/autostart"


def launcher(entry, app):
    return common.HOME / ".local/share/applications" / f"{entry['where']}-{os.path.basename(app)}"


def login_file(entry, app):
    return AUTOSTART / f"evenkeel-os-{entry['where']}-{os.path.basename(app)}"


def starts_at_login(entry):
    return any(login_file(entry, a).exists() for a in entry.get("apps", []))


def set_login(entry, on):
    """Start a box app at login, or stop; True if it worked."""
    done = False
    for a in entry.get("apps", []):
        f = login_file(entry, a)
        if not on:
            f.unlink(missing_ok=True)
            done = True
            continue
        try:
            text = launcher(entry, a).read_text()
        except OSError:         # the app's launcher is gone: nothing to switch
            continue
        text = re.sub(r"(?m)^(X-GNOME-Autostart-[^=]*|Hidden|NoDisplay)=.*\n?", "", text)
        head, sep, rest = text.partition("[Desktop Entry]\n")
        AUTOSTART.mkdir(parents=True, exist_ok=True)
        f.write_text(head + sep + "X-GNOME-Autostart-enabled=true\n" + rest)
        done = True
        break                       # the app's main entry is enough
    return done


def login():
    """Start Apps at Login: choose box apps that start by themselves when you log in."""
    apps = [r for r in app_list.load() if r["where"].startswith("evenkeel-") and r.get("apps")]
    if not apps:
        say("No downloaded apps that can start at login are installed. Apps from Bazaar, the app store, have this "
            "setting inside the app.")
        return 0
    rows = [[r["title"], common.WHERE.get(r["where"], r["where"]), "Yes" if starts_at_login(r) else "No"] for r in apps]
    i = choose("Which app should start, or stop starting, when you log in?",
               ["App", "Installed in", "Starts at login"], rows)
    if i is None:
        return 1
    entry = apps[i]
    on = not starts_at_login(entry)
    if not set_login(entry, on):
        windows.failed(f"Changing {entry['title']}", reason=f"{entry['title']} is missing from Show Apps. "
                                                    f"Install it again to put it back.")
        return 1
    say(f"{entry['title']} will start when you log in." if on else
        f"{entry['title']} will no longer start when you log in.")
    return 0


LOGIN_CHECKED = common.STATE.with_name("login-entries-checked.json")


def save_login_checked(checked):
    LOGIN_CHECKED.parent.mkdir(parents=True, exist_ok=True)
    LOGIN_CHECKED.write_text(json.dumps(checked))


def login_checked():
    """Login entries already checked and not from a box: {path: modified time}."""
    try:
        return json.loads(LOGIN_CHECKED.read_text())
    except (OSError, ValueError):
        return {}


def unchecked(f, checked):
    try:
        return checked.get(str(f)) != f.stat().st_mtime
    except OSError:
        return False


def fix_app_login_files():
    """Point an app's own open-at-login entry at its box (Discord); returns how many were fixed."""
    fixed = 0
    by_box = {}
    for r in app_list.load():
        if r["where"].startswith("evenkeel-") and r.get("apps"):
            by_box.setdefault(r["where"], []).append(r)
    if not by_box or not AUTOSTART.is_dir():
        return 0
    checked = login_checked()
    for f in sorted(AUTOSTART.glob("*.desktop")):
        if f.name.startswith("evenkeel-os-") or not unchecked(f, checked):
            continue
        try:
            text = f.read_text()
        except OSError:         # removed while we looked
            continue
        if launchers.BOX_RUN in text or re.search(r"(?m)^(Hidden=true|X-GNOME-Autostart-enabled=false)$", text):
            continue        # already fixed, or switched off
        m = re.search(r"(?m)^Exec=(.*)$", text)
        try:
            first = shlex.split(m.group(1))[0] if m else ""
        except (ValueError, IndexError):        # a broken Exec line: leave the file as it is
            continue
        if not first.startswith("/") or os.path.exists(first):
            continue
        box = next((b for b in by_box if boxes.box_exists(b) and subprocess.run(
            boxes.in_box(b, "test", "-x", first), capture_output=True).returncode == 0), None)
        if not box:
            checked[str(f)] = f.stat().st_mtime         # not from a box: do not look again until it changes
            save_login_checked(checked)
            continue
        new = text.replace(m.group(0), f"Exec={launchers.BOX_RUN} {box} {m.group(1).strip()}", 1)
        f.write_text(new)
        fixed += 1
        if not app_running(os.path.basename(first)):
            subprocess.Popen(["gio", "launch", str(f)], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return fixed


def app_running(key):
    state = Path(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}") / "evenkeel-os-box-apps"
    for pidf in state.glob(f"{key}.*.pid"):
        try:
            os.kill(int(pidf.read_text().strip()), 0)
            return True
        except (OSError, ValueError):           # a stale or broken pid file: that copy isn't running
            continue
    return False


def app_login_files_to_fix():
    """Cheap test for login: are there login entries pointing at a path the system does not have?"""
    if not AUTOSTART.is_dir() or not any(r["where"].startswith("evenkeel-") for r in app_list.load()):
        return False
    checked = login_checked()
    for f in AUTOSTART.glob("*.desktop"):
        if f.name.startswith("evenkeel-os-") or not unchecked(f, checked):
            continue
        try:
            m = re.search(r"(?m)^Exec=(\S+)", f.read_text())
        except OSError:         # removed while we looked
            continue
        if m and m.group(1).startswith("/") and launchers.BOX_RUN not in m.group(1) and not os.path.exists(m.group(1)):
            return True
    return False
