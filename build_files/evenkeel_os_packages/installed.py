"""Spotting an app that is already installed."""
import re
import shlex
import subprocess

import evenkeel_os_health as health
from evenkeel_os_ui import LAUNCH_ENV, _, ask, say
from evenkeel_os_packages import app_list, boxes, common, update_notes

# Only version characters: a version is read from the downloaded file and goes into rpm's Lua below.
VERSION = re.compile(r"^[\w.+~^:-]+$")


def box_version(kind, name):
    """Version of a package in its box ('' if not installed there, or no box)."""
    box = common.BOXES[kind]["name"]
    if not boxes.box_exists(box):
        return ""
    if kind == "rpm":
        cmd = f"rpm -q --qf '%{{EPOCHNUM}}:%{{VERSION}}-%{{RELEASE}}' {shlex.quote(name)}"
    else:
        cmd = f"dpkg-query -W -f='${{db:Status-Status}} ${{Version}}' {shlex.quote(name)}"
    r = subprocess.run(boxes.in_box(box, "sh", "-c", cmd), capture_output=True, text=True)
    out = r.stdout.strip()
    if r.returncode != 0 or not out:
        return ""
    if kind == "deb":
        state, _sep, ver = out.partition(" ")
        return ver if state == "installed" else ""
    return out


def host_version(name):
    r = subprocess.run(["rpm", "-q", "--qf", "%{EPOCHNUM}:%{VERSION}-%{RELEASE}", name], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def compare(kind, a, b):
    """-1, 0 or 1 as version a is older, the same or newer than b."""
    if a == b or not all(VERSION.match(v) for v in (a, b)):
        return 0
    if kind == "rpm":
        lua = f"%{{lua: print(rpm.vercmp('{a}', '{b}'))}}"
        r = subprocess.run(["rpm", "--eval", lua], capture_output=True, text=True)
        try:
            return max(-1, min(1, int(r.stdout.strip())))
        except ValueError:
            return 0
    box = common.BOXES["deb"]["name"]
    for op, res in (("lt", -1), ("gt", 1)):
        cmp = boxes.in_box(box, "dpkg", "--compare-versions", a, op, b)
        if subprocess.run(cmp, capture_output=True).returncode == 0:
            return res
    return 0


def plain_version(v):
    """Version without the leading epoch and release noise people do not need to see ('0:1.2-3' -> '1.2-3')."""
    return re.sub(r"^\d+:", "", v)


def system_requested():
    """Package names added to the version that starts next, or None if rpm-ostree can't say."""
    ds = health.deployments()
    return health.requested(ds[0]) if ds else None


def flatpak_installed(app_id):
    return bool(app_id) and subprocess.run(["flatpak", "info", app_id], capture_output=True).returncode == 0


def norm_name(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def open_app(entry):
    """Start an installed app the way its app grid entry does. False when it has no window to open."""
    if entry["where"] in common.FLATPAK_PLACES:
        cmd = ["flatpak", "run", entry["package"]]
    else:
        files = [common.launcher(entry["where"], a) for a in entry.get("apps", [])]
        f = next((f for f in files if f.exists()), None)
        if not f:
            return False
        cmd = ["gio", "launch", str(f)]
    try:
        subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         env=LAUNCH_ENV)
    except OSError:
        say(_("{title} didn't open.").format(title=entry["title"]), kind="error")
    return True


def from_bazaar(pkg, info, title, record):
    """The app is already installed from Bazaar: 'ok' opens it, 'extra' installs the file too, None stops."""
    a = ask(_("{title} is already installed from Bazaar, the app store.\n\nRecommended: Open it.").format(title=title)
            + "\n\n" + update_notes.second_copy(pkg, info, _("Install the file too")),
            ok=_("Open it"), extra=_("Install the file too"))
    if a == "ok":
        open_app(record)
    return a


def already_installed(pkg, info, title):
    """Ask what to do if the app is already installed; returns (go_on, mode, exit code)."""
    records = app_list.load()
    ours = common.BOXES[pkg.kind]["name"]

    # 1. On the system itself
    hv = host_version(pkg.name) if pkg.kind == "rpm" else ""
    if hv:
        mine = next((r for r in records if r["where"] == "system" and r["package"] == pkg.name), None)
        if not mine:
            say(_("{title} is already part of EvenKeelOS. Nothing to install.").format(title=title))
            return False, "", 0
        if mine.get("from_fedora"):
            say(_("{title} is already installed from Fedora and stays up to date. You don't need this file.")
                .format(title=title))
            return False, "", 0
        c = compare("rpm", pkg.evr, hv)
        if c <= 0:
            if c == 0:
                say(_("{title} is already installed. This file is the same version.").format(title=title))
            else:
                say(_("{title} is already installed. This file is older than the one installed.").format(title=title))
            return False, "", 0
        if ask(_("Update {title} to the newer version in this file?\n\nNeeds your password and a restart.")
               .format(title=title), ok=_("Update")) != "ok":
            return False, "", 1
        return True, "system-update", 0

    # 2. In its box
    bv = box_version(pkg.kind, pkg.name)
    if bv:
        mine = next((r for r in records if r["where"] == ours and r["package"] == pkg.name),
                    {"title": title, "where": ours, "apps": list(info["apps"])})
        c = compare(pkg.kind, pkg.evr, bv)
        if c == 0:
            a = ask(_("{title} is already installed.\n\nRecommended: Open it.\n\nOr Reinstall: installs it again "
                      "from this file. Only needed if it isn't working.").format(title=title),
                    ok=_("Open it"), extra=_("Reinstall"))
            if a == "ok":
                if not open_app(mine):
                    say(_("{title} has no window to open. It is a tool other apps use.").format(title=title))
                return False, "", 0
            return (True, "reinstall", 0) if a == "extra" else (False, "", 1)
        if c > 0:
            if ask(_("Update {title} to the newer version in this file?").format(title=title),
                   ok=_("Update")) != "ok":
                return False, "", 1
            return True, "update", 0
        if ask(_("This file is an older version of {title} than the one you have.\n\nInstall the older version: "
                 "replaces yours. Only do this if the newer one has a problem.").format(title=title),
               ok=_("Install the older version")) != "ok":
            return False, "", 1
        return True, "older", 0

    # 3. From Flathub, or 4. in the other box (same app name)
    want = {norm_name(title), norm_name(pkg.name)}
    for r in records:
        if r["where"] == "flathub" and (norm_name(r["title"]) in want) and flatpak_installed(r["package"]):
            a = from_bazaar(pkg, info, r["title"], r)
            if a == "ok":
                return False, "", 0
            return (True, "install", 0) if a == "extra" else (False, "", 1)
        if r["where"] in (common.BOXES["rpm"]["name"], common.BOXES["deb"]["name"]) and r["where"] != ours and \
                norm_name(r["title"]) in want:
            if r["where"] == common.BOXES["rpm"]["name"]:
                head = _("{title} is already installed from an .rpm file.")
            else:
                head = _("{title} is already installed from a .deb file.")
            a = ask(head.format(title=r["title"]) + "\n\n" + _("Recommended: Open it.") + "\n\n" +
                    update_notes.second_copy(pkg, info, _("Install it here too")),
                    ok=_("Open it"), extra=_("Install it here too"))
            if a == "ok":
                open_app(r)
                return False, "", 0
            return (True, "install", 0) if a == "extra" else (False, "", 1)
    return True, "install", 0
