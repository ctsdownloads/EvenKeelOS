#!/usr/bin/python3 -I
"""Build step: the list Network safety's Let an app in picks from, written to evenkeel_os_letin.APPS.

Three sources: the apps checked by hand (let-in-checked.txt, each with the page that states its ports), firewalld's
own services in this image, and IANA's port list in this image's /etc/services. Fails the build when a source is
missing or a checked app's ports aren't valid.

Run as:  python3 -I make-let-in-apps.py LIBDIR CHECKED_LIST
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import evenkeel_os_letin as letin  # noqa: E402

IANA = Path("/etc/services")
problems = []


def checked(path):
    """NAME | PORTS (space separated) | LINK | ABOUT, one app a line; # starts a comment."""
    out = []
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) != 4:
            problems.append(f"{path} line {n}: needs NAME | PORTS | LINK | ABOUT")
            continue
        name, specs, link, about = cols
        got = letin.ports(specs.split())
        if not got or not letin.label(name) or not link.startswith("https://"):
            problems.append(f"{path} line {n}: a bad name, port or link: {line}")
            continue
        out.append({"name": name, "about": about, "service": "", "ports": got, "source": "checked", "link": link})
    return out


def firewalld():
    out = []
    for f in sorted(letin.SERVICES.glob("*.xml")):
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            problems.append(f"{f} isn't valid XML")
            continue
        name = f.stem
        if not letin.SERVICE_NAME.match(name) or name.startswith("evenkeel-"):
            continue
        short = " ".join((root.findtext("short") or name).split())
        about = " ".join((root.findtext("description") or "").split())
        found = [letin.port(f"{p.get('port')}/{p.get('protocol')}") for p in root.findall("port")]
        out.append({"name": letin.label(short) or name, "about": about, "service": name,
                    "ports": [p for p in found if p], "source": "firewalld",
                    "link": f"https://github.com/firewalld/firewalld/blob/main/config/services/{name}.xml"})
    return out


def iana():
    """One entry a name, its TCP and UDP ports together; IANA's own words as the description."""
    names = {}
    for line in IANA.read_text(errors="replace").splitlines():
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._+-]*)\s+([0-9]+)/(tcp|udp)\b[^#]*(?:#\s*(.*))?$", line)
        if not m:
            continue
        name, number, proto, about = m[1], m[2], m[3], " ".join((m[4] or "").split())
        spec = letin.port(f"{number}/{proto}")
        if not spec:
            continue
        e = names.setdefault(name, {"name": name, "about": about, "service": "", "ports": [], "source": "IANA",
                                    "link": "https://www.iana.org/assignments/service-names-port-numbers/"})
        if spec not in e["ports"]:
            e["ports"].append(spec)
        e["about"] = e["about"] or about
    return [e for e in names.values() if letin.label(e["name"])]


everything = checked(sys.argv[2]) + firewalld() + iana()
counts = {s: sum(a["source"] == s for a in everything) for s in ("checked", "firewalld", "IANA")}
if counts["firewalld"] < 200:
    problems.append(f"only {counts['firewalld']} firewalld services were found in {letin.SERVICES}")
if counts["IANA"] < 1000:
    problems.append(f"only {counts['IANA']} IANA entries were found in {IANA}")
if problems:
    sys.exit("ERROR: Let an app in's list:\n  " + "\n  ".join(problems))
letin.APPS.parent.mkdir(parents=True, exist_ok=True)
letin.APPS.write_text(json.dumps(everything, indent=0))
print("Let an app in: " + ", ".join(f"{n} from {s}" for s, n in counts.items()))
