"""Download sources, update notes and hardware rule records."""
import os
import re
import shutil
import subprocess
from evenkeel_os_packages import boxes, common



REPO_DIRS = {"rpm": "/etc/yum.repos.d", "deb": "/etc/apt/sources.list.d"}
REPO_FILE = re.compile(r"^/etc/(yum\.repos\.d/[^/]+\.repo|apt/sources\.list\.d/[^/]+\.(list|sources))$")


def box_repos(box, kind):
    """Download-source files in a box: name -> contents."""
    r = subprocess.run(boxes.in_box(box, "sh", "-c", f"cd {REPO_DIRS[kind]} 2>/dev/null && for f in *; do "
                                               f"[ -f \"$f\" ] && printf '\\n==> %s\\n' \"$f\" && cat \"$f\"; done"),
                       capture_output=True, text=True)
    out = {}
    for part in r.stdout.split("\n==> ")[1:]:
        name, _, text = part.partition("\n")
        out[name.strip()] = text
    return out


def adds_source(pkg):
    """Does the package itself carry a download source (a repository) for updates?"""
    return any(REPO_FILE.match(p) for p in pkg.files)


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
