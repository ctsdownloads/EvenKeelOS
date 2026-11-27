"""Shared folders: folders in your home folder that computers on a Home network can open, with one password."""
import json
import os
import pwd
import stat
import subprocess
from pathlib import Path

from evenkeel_os_ui import _, N_

STATE = Path("/etc/evenkeel-os/shared-folders.json")
SHARES = Path("/etc/samba/evenkeel-shares.conf")
SMB_CONF = Path("/etc/samba/smb.conf")
INCLUDE = f"include = {SHARES}"
MODES = {"ro": N_("Read only"), "rw": N_("Read and write")}
FIREWALL_SERVICE = "evenkeel-sharing"
NOT_IN_NAMES = set('[]"/\\:;|<>+=,*?%')
TAKEN = {"global", "homes", "printers", "print$", "ipc$"}
MIN_PASSWORD = 8


def load():
    """The saved list: {"on": bool, "folders": [{"path", "owner", "mode", "name"}], "passwords": [user names]}."""
    try:
        s = json.loads(STATE.read_text())
    except (OSError, ValueError):
        s = {}
    folders = [f for f in s.get("folders", []) if isinstance(f, dict) and f.get("mode") in MODES and
               all(isinstance(f.get(k), str) and clean(f[k]) for k in ("path", "owner", "name"))]
    return {"on": s.get("on") is True, "folders": folders,
            "passwords": [u for u in s.get("passwords", []) if isinstance(u, str)]}


def clean(text):
    """No control characters, and real text (a name in an old encoding can't be written to Samba's settings)."""
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return not any(ord(c) < 32 or ord(c) == 127 for c in text)


def folder_problem(path, user):
    """Why user can't share path ("" when they can). path must already be the real path, with no shortcuts in it."""
    try:
        home = os.path.realpath(pwd.getpwnam(user).pw_dir)
        st = os.lstat(path)
    except (KeyError, OSError):
        return _("That folder wasn't found.")
    if not path.startswith("/") or os.path.realpath(path) != path or not clean(path) or "%" in path \
            or "\\" in path or path != path.strip() or len(path) > 1024:
        return _("That folder's name can't be shared. Rename it or pick another.")
    if not stat.S_ISDIR(st.st_mode):
        return _("Pick a folder, not a file.")
    if path == home or not path.startswith(home + "/"):
        return _("Pick a folder inside your home folder.")
    if any(part.startswith(".") for part in path[len(home) + 1:].split("/")):
        return _("Hidden folders hold settings and keys. They can't be shared.")
    if st.st_uid != pwd.getpwnam(user).pw_uid:
        return _("That folder belongs to someone else.")
    return ""


def share_name(path, taken):
    """The name other computers show: the folder's own name, made safe and different from the others."""
    base = "".join(" " if c in NOT_IN_NAMES or not clean(c) else c for c in os.path.basename(path))
    base = " ".join(base.split())[:60] or "Shared folder"
    if base.lower() in TAKEN:
        base += " folder"
    name, n = base, 2
    while name.lower() in {t.lower() for t in taken}:
        name, n = f"{base} {n}", n + 1
    return name


def shares_conf(state):
    """SHARES for the saved list; folders whose owner has no sharing password are left out."""
    out = ["# Written by Wheelhouse, Shared folders. Changes here are replaced.\n"]
    for f in state["folders"]:
        if f["owner"] not in state["passwords"]:
            continue
        out.append(f"\n[{f['name']}]\n\tpath = {f['path']}\n\tvalid users = {f['owner']}\n"
                   f"\tread only = {'yes' if f['mode'] == 'ro' else 'no'}\n\tbrowseable = yes\n")
    return "".join(out)


def set_up():
    """Whether smb.conf still reads the folder list (it was replaced on this computer if not)."""
    try:
        return any(line.strip() == INCLUDE for line in SMB_CONF.read_text().splitlines())
    except OSError:
        return False


def running():
    """Whether Samba is running, or starting (its start may still be waiting in systemd's queue)."""
    try:
        state = subprocess.run(["systemctl", "is-active", "smb.service"], capture_output=True, text=True,
                               timeout=20).stdout.strip()
        queued = subprocess.run(["systemctl", "list-jobs", "--no-legend", "smb.service"], capture_output=True,
                                text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return False
    return state in ("active", "activating", "reloading") or bool(queued)
