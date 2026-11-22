"""Packages that only add a download source."""
import os
import platform
import re
import shlex
import shutil
import subprocess

from evenkeel_os_ui import ask, choose, say
from evenkeel_os_packages import app_list, boxes, common, install_file, targets, windows


SOURCED = set()      # packages installed from a download source in this run: System Update keeps them current
FROM_SOURCE = common.CACHE / "from-source"


def source_packages(kind, box, sources):
    """[(package, summary)] offered by the download sources the box just got."""
    if kind == "rpm":
        ids = [i for i, _, on in sources if on]
        r = subprocess.run(boxes.in_box(box, "dnf", "-q", "repoquery", "--repo=" + ",".join(ids), "--latest-limit=1",
                                        f"--arch={platform.machine()},noarch", "--queryformat=%{name}\t%{summary}\n"),
                           capture_output=True, text=True)
        rows = [line.split("\t", 1) for line in r.stdout.splitlines() if "\t" in line]
    else:
        # Ubuntu keeps each source's package list compressed, named after its address, one per processor type.
        marks = [re.sub(r"^\w+://", "", url).rstrip("/").replace("/", "_") + "_" for url, _, on in sources if on]
        arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine(), platform.machine())
        new = [f for f in apt_lists(box) if any(os.path.basename(f).startswith(m) for m in marks) and
               re.search(rf"_binary-({arch}|all)_Packages(\.\w+)?$", f)]
        rows, name = [], None
        if new:
            r = subprocess.run(boxes.in_box(box, "sh", "-c", "for f in " + " ".join(shlex.quote(f) for f in new) +
                                            "; do /usr/lib/apt/apt-helper cat-file \"$f\"; done | "
                                            "grep -E '^(Package|Description):'"), capture_output=True, text=True)
            for line in r.stdout.splitlines():
                if line.startswith("Package:"):
                    name = line.split(":", 1)[1].strip()
                    rows.append([name, ""])
                elif line.startswith("Description:") and rows and not rows[-1][1]:
                    rows[-1][1] = line.split(":", 1)[1].strip()
    seen, out = set(), []
    for n, summary in sorted(rows, key=lambda r: r[0].lower()):
        n = n.strip()
        if n and n not in seen and not re.search(r"-(devel|dev|debuginfo|debugsource|dbg|doc|docs)$", n):
            seen.add(n)
            out.append((n, summary.strip()))
    return out


def apt_lists(box):
    r = subprocess.run(boxes.in_box(box, "sh", "-c", "ls -d /var/lib/apt/lists/*_Packages* 2>/dev/null"),
                       capture_output=True, text=True)
    return r.stdout.split()


def install_source(pkg, info):
    """A package that only adds a download source: add it to the box, then pick an app from it."""
    box = common.BOXES[pkg.kind]
    names = [n for _, n, on in info["sources"] if on] or [pkg.name]
    shown = "\n".join("  - " + n for n in names[:6])
    title = f"{pkg.name} (download source)"
    new_box = not boxes.box_exists(box["name"])
    text = (f"{pkg.path.name} has no app in it. It adds a place to download apps from:\n{shown}\n\n"
            f"Add it: adds it to the {box['label']}, then you pick an app from it. Apps from it update "
            f"automatically.")
    size = None
    if new_box:
        intro, size = boxes.first_time(pkg.kind)
        text += "\n\n" + intro
    if ask(text, ok="Set up and add it" if new_box else "Add it") != "ok":
        return 1
    if new_box:
        if not boxes.room_for(boxes.setup_need(size)) or not boxes.setup_box(pkg.kind, size):
            return 1
    have = next((r for r in app_list.load() if r["where"] == box["name"] and r["package"] == pkg.name), None)
    if not have and targets.box_install(pkg, info, title, quiet=True) != 0:
        return windows.failed(f"Adding the download source {pkg.name}")
    if pkg.kind == "deb":
        if not windows.run_steps("Getting the list of apps from the new download source.",
                                 [boxes.in_box(box["name"], "sudo", "apt-get", "update")]):
            return windows.failed(f"Reading the download source {pkg.name}")
    windows.mark_busy("Reading the list of apps from the new download source")
    apps = source_packages(pkg.kind, box["name"], info["sources"])
    if not apps:
        say(f"The download source was added, but it has no apps to show right now. Check your internet "
            f"connection, then open {pkg.path.name} again.", "warning")
        return 0
    i = choose("Which app do you want? Start typing its name.", ["App", "About it"], [list(a) for a in apps])
    if i is None:
        say(f"The download source stays. Open {pkg.path.name} again to pick an app, or remove it in System Tools, "
            f"Apps, Remove apps.")
        return 0
    name = apps[i][0]
    folder = FROM_SOURCE / pkg.kind
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    cmd = ["dnf", "-q", "download", f"--destdir={folder}", name] if pkg.kind == "rpm" else \
        ["sh", "-c", f"cd {shlex.quote(str(folder))} && apt-get download {shlex.quote(name)}"]
    if not windows.run_steps(f"Downloading {name}.", [boxes.in_box(box["name"], *cmd)]):
        return windows.failed(f"Downloading {name}")
    files = sorted(folder.glob("*.rpm" if pkg.kind == "rpm" else "*.deb"))
    if not files:
        return windows.failed(f"Downloading {name}", reason=f"{name} could not be downloaded from the source.")
    # keep the file where Repair can find it again, like any installed file
    keep = common.CACHE / files[0].name
    shutil.move(str(files[0]), keep)
    SOURCED.add(name)
    return install_file.install(str(keep))
