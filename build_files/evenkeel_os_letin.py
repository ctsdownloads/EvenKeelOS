"""Network safety, Let in: apps and ports a place lets in, on top of what the place itself allows."""
import json
import re
from pathlib import Path

STATE = Path("/etc/evenkeel-os/let-in.json")
APPS = Path("/usr/share/evenkeel-os/let-in-apps.json")
SERVICES = Path("/usr/lib/firewalld/services")
ZONES = Path("/usr/lib/firewalld/zones")
SERVICE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+-]{0,63}$")
PORT = re.compile(r"^([0-9]{1,5})(?:-([0-9]{1,5}))?/(tcp|udp)$")
MAX_PORTS = 20
MAX_LABEL = 60


def port(spec):
    """A port or range with its protocol ("8096/tcp", "2456-2458/udp"), tidied; "" when it isn't one."""
    m = PORT.match(spec)
    if not m:
        return ""
    low, high = int(m[1]), int(m[2] or m[1])
    if not 1 <= low <= high <= 65535:
        return ""
    return f"{low}/{m[3]}" if low == high else f"{low}-{high}/{m[3]}"


def ports(specs):
    """All the ports tidied, or None when any isn't a port, there are none, or there are too many."""
    out = [port(s) for s in specs]
    return out if out and len(out) <= MAX_PORTS and all(out) and len(set(out)) == len(out) else None


def label(text):
    """The name shown for an opening, tidied; "" when it can't be used."""
    text = " ".join(text.split())
    ok = 0 < len(text) <= MAX_LABEL and not any(ord(c) < 32 or ord(c) == 127 for c in text)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        ok = False
    return text if ok else ""


def load():
    """{zone: [{"id", "label", "service", "ports"}]}: what each place lets in beyond its own settings."""
    try:
        s = json.loads(STATE.read_text())
    except (OSError, ValueError):
        s = {}
    out = {}
    for zone, entries in (s.items() if isinstance(s, dict) else ()):
        if isinstance(entries, list):
            out[zone] = [e for e in entries if isinstance(e, dict) and isinstance(e.get("id"), str)
                         and label(e.get("label", "")) and isinstance(e.get("service", ""), str)
                         and isinstance(e.get("ports"), list) and all(isinstance(p, str) for p in e["ports"])]
    return out


def apps():
    """The list to pick from: [{"name", "about", "service", "ports", "source", "link"}], or [] when missing."""
    try:
        a = json.loads(APPS.read_text())
    except (OSError, ValueError):
        return []
    return a if isinstance(a, list) else []


def find(text, everything, most=60):
    """Apps whose name, description or port matches every word typed; firewalld's and checked ones first."""
    words = text.lower().split()
    out = []
    for a in everything:
        hay = " ".join([a["name"], a["about"], a["service"], *a["ports"]]).lower()
        if all(w in hay for w in words):
            out.append(a)
            if len(out) >= most and words:
                break
    return out


def zone_base(zone):
    """The services and ports a place has from its own settings (shipped zone file), which Let in never removes."""
    try:
        text = (ZONES / f"{zone}.xml").read_text()
    except OSError:
        return set(), set()
    return (set(re.findall(r'<service name="([^"]+)"', text)),
            {f"{p}/{proto}" for proto, p in re.findall(r'<port protocol="(tcp|udp)" port="([0-9-]+)"', text)})
