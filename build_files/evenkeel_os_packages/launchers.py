"""Show Apps launchers for box apps."""
import os
import re
import shlex
import subprocess
from evenkeel_os_packages import app_list, boxes, common, login_apps
from evenkeel_os_ui import _


BOX_RUN = "/usr/libexec/evenkeel-os-box-run"
QUIT = "evenkeel-quit"


def fix_launcher(path, box):
    """Point a box app's launcher at evenkeel-os-box-run and fix its StartupWMClass so the dock shows its icon."""
    try:
        text = path.read_text()
    except OSError:
        return False
    old = text
    if BOX_RUN not in text:
        key = ""

        def swap(m):
            nonlocal key
            rest = m.group(2).strip()
            try:
                first = shlex.split(rest)[0]
            except (ValueError, IndexError):
                return m.group(0)
            key = key or os.path.basename(first)
            return f"Exec={BOX_RUN} {m.group(1)} {rest}"
        text = re.sub(r"(?m)^Exec=\S*distrobox-enter\s+-n\s+(\S+)\s+(?:\S+\s+)*?--\s+(.*)$", swap, text)
        if not key:
            return False
        name = re.search(r"(?m)^Name=(.*)$", text)
        head, sep, rest = text.partition("[Desktop Entry]\n")
        if re.search(r"(?m)^Actions=", rest.split("\n[", 1)[0]):
            rest = re.sub(r"(?m)^(Actions=[^\n]*?);?[ \t]*$", lambda m: f"{m.group(1)};{QUIT};", rest, count=1)
        else:
            rest = f"Actions={QUIT};\n" + rest
        app = name.group(1) if name else key
        # The file keeps English; the person's language is added as Name[de_DE]= and the like.
        here = _("Quit {app}").format(app=app)
        lang = re.sub(r"\.[^@]*", "", os.environ.get("LANG", ""))
        local = f"Name[{lang}]={here}\n" if lang and here != f"Quit {app}" else ""
        text = head + sep + rest.rstrip("\n") + (
            f"\n\n[Desktop Action {QUIT}]\nName=Quit {app}\n{local}"
            f"Exec={BOX_RUN} --stop {key}\n")
    if not wm_class_ok(text, path, box):
        text = re.sub(r"(?m)^StartupWMClass=.*\n?", "", text)
        head, sep, rest = text.partition("[Desktop Entry]\n")
        text = head + sep + f"StartupWMClass={window_name(path, box)}\n" + rest
    if text != old:
        path.write_text(text)
    return True


def window_name(path, box):
    """The name the app's window goes by: its own entry's name, without the box's name in front."""
    return path.name.removeprefix(f"{box}-").removesuffix(".desktop")


def wm_class_ok(text, path, box):
    return re.findall(r"(?m)^StartupWMClass=(.*)$", text) == [window_name(path, box)]


def launchers_to_fix():
    """App grid entries made before evenkeel-os-box-run existed, or before the dock showed box apps' icons."""
    apps_dir = common.HOME / ".local/share/applications"
    out = []
    for r in app_list.load():
        if r["where"] in common.WHERE and r["where"].startswith("evenkeel-"):
            for a in r.get("apps", []):
                f = apps_dir / f"{r['where']}-{os.path.basename(a)}"
                if f.exists():
                    text = f.read_text()
                    if BOX_RUN not in text or not wm_class_ok(text, f, r["where"]):
                        out.append((f, r["where"]))
    return out


def export(box, info):
    """Put the package's apps in the app grid, or its commands on the PATH. Returns what was exported."""
    apps_dir = common.HOME / ".local/share/applications"
    done_apps, done_bins = [], []
    for path in info["apps"]:
        r = subprocess.run(boxes.in_box(box, "distrobox-export", "--app", path, "--export-label", "none"),
                           capture_output=True, text=True)
        exported = apps_dir / f"{box}-{os.path.basename(path)}"
        if r.returncode == 0 and exported.exists():
            fix_launcher(exported, box)
            done_apps.append(path)
    if done_apps:
        icons_changed()
    if not done_apps:
        bindir = common.HOME / ".local/bin"
        bindir.mkdir(parents=True, exist_ok=True)
        for b in info["bins"]:
            r = subprocess.run(boxes.in_box(box, "distrobox-export", "--bin", b, "--export-path", str(bindir)),
                               capture_output=True, text=True)
            if r.returncode == 0:
                done_bins.append(b)
    return done_apps, done_bins


def icons_changed():
    """Touch the icon folders so GNOME picks up new app icons now, not at the next login."""
    for d in (common.HOME / ".local/share/icons/hicolor", common.HOME / ".local/share/icons"):
        if d.is_dir():
            os.utime(d)


def unexport(entry):
    box = entry["where"]
    apps_dir = common.HOME / ".local/share/applications"
    for path in entry.get("apps", []):        # quit the app first if it is running
        try:
            m = re.search(r"--stop (\S+)", (apps_dir / f"{box}-{os.path.basename(path)}").read_text())
        except OSError:
            m = None
        if m and os.access(BOX_RUN, os.X_OK):
            subprocess.run([BOX_RUN, "--stop", m.group(1)], capture_output=True,
                           env={**os.environ, "EVENKEEL_QUIET": "1"})
    login_apps.set_login(entry, False)
    for path in entry.get("apps", []):
        if boxes.box_exists(box):
            subprocess.run(boxes.in_box(box, "distrobox-export", "--app", path, "--delete"), capture_output=True)
        (apps_dir / f"{box}-{os.path.basename(path)}").unlink(missing_ok=True)
    for b in entry.get("bins", []):
        if boxes.box_exists(box):
            subprocess.run(boxes.in_box(box, "distrobox-export", "--bin", b,
                                        "--export-path", str(common.HOME / ".local/bin"), "--delete"),
                           capture_output=True)
        (common.HOME / ".local/bin" / os.path.basename(b)).unlink(missing_ok=True)
    if entry.get("apps"):
        icons_changed()
