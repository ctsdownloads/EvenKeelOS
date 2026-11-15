"""Download sources, update notes and hardware rule records."""
import os
import re
import shutil
import subprocess
from evenkeel_os_packages import boxes, common


# Fedora 45 keeps its own sources in /usr/share/dnf5/repos.d.
REPO_DIRS = {"rpm": ("/etc/yum.repos.d", "/usr/share/dnf5/repos.d"), "deb": ("/etc/apt/sources.list.d",)}
REPO_FILE = re.compile(r"^/(etc/yum\.repos\.d/[^/]+\.repo|usr/share/dnf5/repos\.d/[^/]+\.repo"
                       r"|etc/apt/sources\.list\.d/[^/]+\.(list|sources))$")


def box_repos(box, kind):
    """Download-source files in a box: name -> contents."""
    files = " ".join(f"{d}/*" for d in REPO_DIRS[kind])
    r = subprocess.run(boxes.in_box(box, "sh", "-c", f"for f in {files}; do [ -f \"$f\" ] && "
                                    f"printf '\\n==> %s\\n' \"${{f##*/}}\" && cat \"$f\"; done"),
                       capture_output=True, text=True)
    out = {}
    for part in r.stdout.split("\n==> ")[1:]:
        name, _, text = part.partition("\n")
        out[name.strip()] = text
    return out


SCRIPT_SOURCE = re.compile(r"/etc/yum\.repos\.d/|/usr/share/dnf5/repos\.d/|/etc/zypp/repos\.d/"
                           r"|sources\.list\.d|sourceparts")


def adds_source(pkg):
    """Does the package, or its install script (Chrome, VS Code), add a download source for updates?"""
    return any(REPO_FILE.match(p) for p in pkg.files) or bool(SCRIPT_SOURCE.search(pkg.scripts))


def file_note(pkg, info):
    """What using the downloaded file means for updates, said before installing."""
    if not adds_source(pkg) or info["blocking"]:
        return "It never updates."
    if info["notes"] and pkg.kind == "rpm":
        return "In a box it updates with System Update; added to the system it never updates."
    return "It adds its maker's download source, so it updates with System Update."


def second_copy(pkg, info, button):
    return f"Or {button}: adds a second copy. {file_note(pkg, info)} You would have two of the same app."


UPDATES_YES = "Updates: automatic, with System Update."
UPDATES_NO = ("Updates: none, because it came from a file. To update, install a newer file. (Some apps, like "
              "Discord, update themselves.)")
UPDATES_FLATHUB = "Updates: automatic."
# A package added from a file stays at that file's version, even with a download source.
UPDATES_FEDORA = "automatic, with System Update."
UPDATES_SYSTEM = "none, because it came from a file. To update, install a newer file."


def add_rules(pkg, info):
    folder = common.CACHE / "rules" / pkg.name
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    paths = []
    for p, text in info["safe_rules"].items():
        f = folder / os.path.basename(p)
        f.write_text(text)
        paths.append(str(f))
    r = subprocess.run(["pkexec", common.HWRULES, "add", pkg.name, *paths], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def remove_rules(name):
    r = subprocess.run(["pkexec", common.HWRULES, "remove", name], capture_output=True, text=True)
    return r.returncode == 0
