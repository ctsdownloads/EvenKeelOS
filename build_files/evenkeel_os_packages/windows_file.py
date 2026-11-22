"""Windows Program: an .exe or .msi opened here; offers its Linux version, or a Linux app that does its job."""
import json
import os
import re
import subprocess
from urllib.parse import urlsplit

from evenkeel_os_ui import ask, say
from evenkeel_os_packages import app_list, artcraft, boxes, common, flathub, installed, repo_apps, vpn, zoom

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
            "code": props.get("ProductCode", "").strip().lower(), "about": props.get("ARPCOMMENTS", "").strip()}


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
            "code": "", "about": f"{info.get('FileDescription', '')} {info.get('Comments', '')}".strip()}


def read_installer(path):
    """Name, maker and MSI product code the installer gives itself; empty when it can't be read."""
    empty = {"name": "", "maker": "", "code": "", "about": ""}
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
            data = json.load(f)
        return data["programs"], data["kinds"]
    except (OSError, ValueError, KeyError):
        return {}, []


def makers_overlap(ours, theirs, least=3):
    """True when two lists of maker keys name the same maker: 'gimp' and 'gimpteam'."""
    return any(len(a) >= least and len(b) >= least and (a in b or b in a) for a in ours for b in theirs)


def same_maker(maker, prog):
    return makers_overlap([norm_maker(maker)], prog["pub"])


def rank(prog):
    """In the browser (chosen over its app) or its company's own Linux version, then its own Linux version from
    Flathub, Fedora or Ubuntu, a hand-picked replacement, an app of its kind."""
    offer = prog["offer"]
    return -1 if offer.get("web") or offer.get("vpn") else 2 if offer.get("kind") else 1 if offer.get("job") else 0


def identify(path, programs, info):
    """(key, how) of the program in the list, or (None, '')."""
    stem = file_stem(path)
    name = norm(re.sub(r"\s+-\s+https?://\S+", "", info["name"]))
    steps = [("product code", lambda p: info["code"] and info["code"] in p["codes"]),
             ("name and maker", lambda p: len(name) >= 3 and name in p["names"]),
             ("file name", lambda p: len(stem) >= 3 and (stem in p["names"] or stem in p["aliases"])),
             # the file name starts with its name or usual file name: 'AcroRdrDCx642600322110_en_US.exe'
             ("file name", lambda p: any(len(n) >= 4 and stem.startswith(n) for n in p["names"]) or
              any(len(a) >= 5 and stem.startswith(a) for a in p["aliases"]))]
    # every step is tried, so a hand-picked replacement beats an app of the same kind found by product code
    found = [(rank(p), i, -max(map(len, p["names"] or [""])), len(k), k, how)
             for i, (how, test) in enumerate(steps) for k, p in programs.items()
             if test(p) and (how == "product code" or not info["maker"] or same_maker(info["maker"], p))]
    return min(found)[4:] if found else (None, "")


def kind_from_words(info, kinds):
    """For a program no list knows: its job, from how the installer describes itself ('Digital Media Player')."""
    text = f" {re.sub(r'[^a-z0-9+]+', ' ', (info['name'] + ' ' + info['about']).lower())} "
    return next((k["offer"] for k in kinds if any(f" {w} " in text for w in k["words"])), None)


def choose(path):
    """(offer, how, info) for a Windows installer: what to offer, how it was worked out, what the file says."""
    programs, kinds = load_list()
    info = read_installer(path)
    key, how = identify(path, programs, info)
    if key:
        return programs[key]["offer"], how, info
    o = kind_from_words(info, kinds)
    return (o, "description", info) if o else (None, "", info)


def offer(o):
    """Where the Linux app comes from: ('web' | 'vpn' | 'flathub' | 'rpm' | 'deb' | 'artcraft', package or address)."""
    for key, where in (("web", "web"), ("vpn", "vpn"), ("flatpak", "flathub"), ("fedora", "rpm"), ("ubuntu", "deb"),
                       ("artcraft", "artcraft")):
        if o.get(key):
            return where, o[key]
    return None, None


def check(path):
    """For build tests: what a file is and what would be offered, without any window."""
    o, how, info = choose(path)
    where, package = offer(o or {})
    print(json.dumps({"file": os.path.basename(path), "name": info["name"], "maker": info["maker"], "how": how,
                      "where": where, "package": package, "kind": None if not o else "browser" if o.get("web")
                      else "same kind" if o.get("kind") else "replacement" if o.get("job") else "same app"}))
    return 0


def installed_record(where, package):
    """How to open the Linux app if it is already installed, or None."""
    if where == "vpn":
        v = vpn.load().get(package)
        return {"where": "system", "package": v["packages"][0]} if v and vpn.is_installed(package) else None
    if where in common.FLATPAK_PLACES:
        app_id = package if where == "flathub" else artcraft.app_id(package)
        return {"where": where, "package": app_id} if installed.flatpak_installed(app_id) else None
    box = common.BOXES[where]["name"]
    return next((r for r in app_list.load() if r["where"] == box and r["package"] == package), None)


def open_file(path):
    o, _, _ = choose(path)
    shown = os.path.basename(path)
    if not o:
        say(f"{shown} is a Windows program. Windows programs can't run here.\n\n"
            f"Look for a Linux version on the maker's website, or search Bazaar, the app store.")
        return 1
    name = o["title"]
    where, package = offer(o)
    if where == "web":
        if ask(f"{shown} is the Windows version of {name}. Here, {name} runs in the web browser instead of its "
               f"own app.\n\nRecommended: Open {name} in the browser.", ok=f"Open {name}", cancel="Close") != "ok":
            return 1
        if zoom.zoom_host(urlsplit(package).hostname or ""):
            return zoom.open_page(package)
        subprocess.Popen(["gio", "open", package], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 0
    if where == "vpn":
        if installed_record(where, package):
            say(f"{shown} is the Windows version of {name}. Its Linux version is already installed. Find it in Show "
                f"Apps.")
            return 0
        return vpn.install(package, intro=f"{shown} is the Windows version of {name}. Windows programs can't run "
                                          f"here, but {name} has a Linux version.\n\n")
    if "job" not in o:
        intro = f"{shown} is the Windows version of {name}. Windows programs can't run here, but {name} has a " \
                f"Linux version"
    else:
        intro = f"{shown} is a Windows program, and Windows programs can't run here. For {o['job']}, {name} does " \
                f"the same job on Linux"
    record = installed_record(where, package)
    if record:
        if ask(f"{intro}, and it is already installed.\n\nRecommended: Open it.", ok=f"Open {name}",
               cancel="Close") == "ok":
            installed.open_app({**record, "title": name})
            return 0
        return 1
    if where == "flathub":
        source, how = "Bazaar, the app store (Flathub)", "It updates by itself."
    elif where == "artcraft":
        source, how = "ArtCraft", "ArtCraft's signature is checked first, and it updates once a day."
    else:
        distro, _, label = boxes.box_words(where)
        first = "" if boxes.box_exists(common.BOXES[where]["name"]) else " " + boxes.first_time(where)[0]
        source, how = distro, f"It goes in the {label} and updates with System Update.{first}"
    if ask(f"{intro}. It comes from {source}.\n\nRecommended: Install {name}. {how}", ok=f"Install {name}",
           cancel="Cancel") != "ok":
        return 1
    if where == "artcraft":
        return artcraft.install(package)
    if where != "flathub":
        return repo_apps.install(where, package, name)
    return flathub.install(package, name)
