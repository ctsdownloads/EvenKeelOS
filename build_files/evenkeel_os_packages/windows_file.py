"""Windows Program: an .exe or .msi opened here; offers its Linux version from Flathub, Fedora or Ubuntu."""
import json
import os
import re
import subprocess

from evenkeel_os_ui import ask, notify, say
from evenkeel_os_packages import app_list, boxes, common, installed, repo_apps, windows

LIST = "/usr/share/evenkeel-os/windows-apps.json"
JUNK = ("the", "team", "software", "inc", "llc", "ltd", "limited", "corporation", "corp", "gmbh", "project",
        "foundation", "developers", "developer", "contributors", "community", "org", "labs")
FILE_WORDS = r"(x86_64|x64|win64|win32|64bit|32bit|amd64|x86|setup|installer|install|windows|win|gui|full|offline|" \
             r"standalone|silent|user|enterprise)"


def norm(s):
    """A name without version, edition and Windows words: 'Mozilla Firefox (x64 en-US)' -> 'mozillafirefox'."""
    s = (s or "").lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\b(for windows|windows|desktop|app|client|x64|x86|64-bit|32-bit|portable|setup|installer|edition|"
               r"the)\b", " ", s)
    s = re.sub(r"\bv?\d+(\.\d+)*\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def trim(p):
    """A maker key without words like 'the', 'team' or 'software' at either end: 'thegimpteam' -> 'gimp'."""
    changed = True
    while changed:
        changed = False
        for j in JUNK:
            if p.startswith(j) and len(p) > len(j) + 3:
                p, changed = p[len(j):], True
            if p.endswith(j) and len(p) > len(j) + 3:
                p, changed = p[:-len(j)], True
    return p


def norm_maker(s):
    s = (s or "").lower()
    s = re.sub(r"\b(inc|llc|ltd|limited|corp|corporation|gmbh|co|company|team|the|project|software|foundation|"
               r"developers?|contributors|community|org|et al)\b", " ", s)
    return trim(re.sub(r"[^a-z0-9]+", "", s))


def file_stem(path):
    """The program's name from its file name: 'putty-64bit-0.85-installer.msi' -> 'putty'."""
    n = re.sub(r"\.(exe|msi)$", "", os.path.basename(path).lower())
    n = re.sub(FILE_WORDS, "", n)
    n = re.sub(r"v?\d+([._-]\d+)*", "", n)
    return re.sub(r"[^a-z]+", "", n)


def read_msi(path):
    r = subprocess.run(["msiinfo", "export", path, "Property"], capture_output=True, text=True, timeout=60)
    props = dict(line.split("\t", 1) for line in r.stdout.splitlines() if "\t" in line)
    return {"name": props.get("ProductName", "").strip(), "maker": props.get("Manufacturer", "").strip(),
            "code": props.get("ProductCode", "").strip().lower()}


def read_exe(path):
    import pefile
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    info = {}
    for group in getattr(pe, "FileInfo", None) or []:
        for entry in group:
            for table in getattr(entry, "StringTable", []):
                for k, v in table.entries.items():
                    info[k.decode(errors="ignore")] = v.decode(errors="ignore").strip()
    pe.close()
    return {"name": info.get("ProductName") or info.get("FileDescription", ""), "maker": info.get("CompanyName", ""),
            "code": ""}


def read_installer(path):
    """Name, maker and MSI product code the installer gives itself; empty when it can't be read."""
    empty = {"name": "", "maker": "", "code": ""}
    try:
        with open(path, "rb") as f:
            head = f.read(8)
        if head.startswith(b"\xd0\xcf\x11\xe0"):        # MSI files are this container format
            return read_msi(path)
        return read_exe(path) if head.startswith(b"MZ") else empty
    except Exception:       # a damaged or unusual file: identify it by its file name only
        return empty


def load_list():
    try:
        with open(LIST) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"matches": {}, "packages": {}}


def same_maker(maker, pkg):
    m = norm_maker(maker)
    return len(m) >= 3 and any(len(p) >= 3 and (m in p or p in m) for p in pkg["pub"])


def identify(path, data):
    """(winget id, how) of the program, or (None, '')."""
    info = read_installer(path)
    pkgs = data["packages"]
    if info["code"]:
        for pid, p in pkgs.items():
            if info["code"] in p["codes"]:
                return pid, "product code"
    name = norm(re.sub(r"\s+-\s+https?://\S+", "", info["name"]))
    if len(name) >= 3:
        hits = [pid for pid, p in pkgs.items() if norm(p["name"]) == name]
        good = [pid for pid in hits if same_maker(info["maker"], pkgs[pid])] if info["maker"] else hits
        if good:
            return min(good, key=len), "name and maker"
    stem = file_stem(path)
    if len(stem) >= 3:
        hits = [pid for pid, p in pkgs.items() if stem in (norm(p["name"]), norm(p["moniker"]))]
        good = [pid for pid in hits if same_maker(info["maker"], pkgs[pid])] if info["maker"] else hits
        if good:
            return min(good, key=len), "file name"
        # the file name starts with the program's name: 'inkscape-1.4.4_2026-05-05_dcaf3e7-x64.signed.msi'
        hits = [pid for pid, p in pkgs.items() if len(norm(p["name"])) >= 4 and stem.startswith(norm(p["name"]))]
        good = [pid for pid in hits if same_maker(info["maker"], pkgs[pid])] if info["maker"] else hits
        if good:
            return max(good, key=lambda pid: (len(norm(pkgs[pid]["name"])), -len(pid))), "file name"
    return None, ""


def offer(m):
    """Where the Linux version comes from: ('flathub' | 'rpm' | 'deb', package), Flathub first."""
    for key, where in (("flatpak", "flathub"), ("fedora", "rpm"), ("ubuntu", "deb")):
        if m.get(key):
            return where, m[key]
    return None, None


def check(path):
    """For build tests: what a file is and what would be offered, without any window."""
    data = load_list()
    pid, how = identify(path, data)
    where, package = offer(data["matches"].get(pid, {})) if pid else (None, None)
    info = read_installer(path)
    print(json.dumps({"file": os.path.basename(path), "name": info["name"], "maker": info["maker"],
                      "program": pid, "how": how, "where": where, "package": package}))
    return 0


def installed_record(where, package):
    box = "flathub" if where == "flathub" else common.BOXES[where]["name"]
    if where == "flathub" and installed.flatpak_installed(package):
        return {"where": "flathub", "package": package}
    return next((r for r in app_list.load() if r["where"] == box and r["package"] == package), None)


def open_file(path):
    data = load_list()
    pid, _ = identify(path, data)
    m = data["matches"].get(pid) if pid else None
    shown = os.path.basename(path)
    if not m:
        say(f"{shown} is a Windows program. Windows programs can't run here.\n\n"
            f"Look for a Linux version on the maker's website, or search Bazaar, the app store.")
        return 1
    name = m["title"]
    where, package = offer(m)
    record = installed_record(where, package)
    if record:
        if ask(f"{shown} is the Windows version of {name}. The Linux version is already installed.\n\n"
               f"Recommended: Open it.", ok="Open it", cancel="Close") == "ok":
            installed.open_app({**record, "title": name})
            return 0
        return 1
    if where == "flathub":
        source, how = "in Bazaar, the app store (Flathub)", "It updates by itself."
    else:
        distro, _, label = boxes.box_words(where)
        first = "" if boxes.box_exists(common.BOXES[where]["name"]) else " " + boxes.first_time(where)[0]
        source, how = f"from {distro}", f"It goes in the {label} and updates with System Update.{first}"
    if ask(f"{shown} is the Windows version of {name}. Windows programs can't run here, but {name} has a Linux "
           f"version {source}.\n\nRecommended: Install the Linux version. {how}",
           ok="Install the Linux version", cancel="Cancel") != "ok":
        return 1
    if where != "flathub":
        return repo_apps.install(where, package, name)
    if windows.run_steps(f"Installing {name} from Flathub.",
                         [["flatpak", "install", "-y", "--noninteractive", "flathub", package]]):
        app_list.remember({"title": name, "package": package, "where": "flathub"})
        notify(f"{name} is installed.")
        say(f"{name} is installed. Find it in Show Apps.")
        return 0
    windows.failed(f"Installing {name}")
    return 1
