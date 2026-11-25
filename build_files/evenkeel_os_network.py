"""Network safety: whether each saved network is Home, Work or a Public place, and what that lets in.

The place is the network's firewall zone, saved in its own NetworkManager profile (connection.zone), so it follows
that one network. A network with no zone gets the default, Public place.
"""
import subprocess

PUBLIC, HOME, WORK = "evenkeel-public", "evenkeel-home", "evenkeel-work"
PLACES = {HOME: "Home", WORK: "Work", PUBLIC: "Public place"}
KINDS = {"802-11-wireless": "Wi-Fi", "802-3-ethernet": "Wired"}
LETS_IN = {
    PUBLIC: "Nothing can reach this computer from the network. Finding printers still works.",
    HOME: "Phones, file sharing and apps you run can reach this computer. System services stay closed unless "
          "switched on below.",
    WORK: "Nothing can reach this computer from the network, and your folders aren't shared. Office shared drives "
          "and printers still work.",
}


def nmcli(*args):
    """nmcli's terse output as lines, or None when it fails."""
    try:
        r = subprocess.run(["nmcli", "-t", *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.splitlines() if r.returncode == 0 else None


def fields(line):
    """One terse line split on its colons; nmcli writes a colon inside a value as \\: and a backslash as \\\\."""
    out, cur, i = [], "", 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line):
            cur += line[i + 1]
            i += 2
        elif line[i] == ":":
            out.append(cur)
            cur, i = "", i + 1
        else:
            cur += line[i]
            i += 1
    return out + [cur]


OPEN = ("", "owe")       # Wi-Fi key management with no password: open, and Enhanced Open (OWE)


class Network:
    def __init__(self, uuid, name, kind, device):
        self.uuid, self.name, self.kind, self.device = uuid, name, kind, device
        self.zone, self.secured = "", False

    @property
    def fixed_public(self):
        """Open Wi-Fi is always a Public place: anyone can make a network with its name."""
        return self.kind == "Wi-Fi" and not self.secured

    @property
    def needs_asking(self):
        """Joined (password accepted), a password Wi-Fi, and never asked. A wired profile isn't asked: it
        matches every cable you plug in, so it stays a Public place unless set in Wheelhouse."""
        return bool(self.device) and not self.zone and self.kind == "Wi-Fi" and self.secured


def networks():
    """Saved Wi-Fi and wired networks, the connected ones first; [] when NetworkManager can't be asked.
    A network counts as connected only once it is fully joined. Hotspots this computer makes are left out: they
    keep NetworkManager's own sharing zone."""
    joined = {}
    for line in nmcli("-f", "UUID,DEVICE,STATE", "connection", "show", "--active") or []:
        f = fields(line)
        if len(f) == 3 and f[2] == "activated":
            joined[f[0]] = f[1]
    out = []
    for line in nmcli("-f", "UUID,TYPE,NAME", "connection", "show") or []:
        f = fields(line)
        if len(f) != 3 or f[1] not in KINDS:
            continue
        n = Network(f[0], f[2], KINDS[f[1]], joined.get(f[0], ""))
        keys = ["connection.zone", "ipv4.method"]
        if n.kind == "Wi-Fi":
            keys += ["802-11-wireless.mode", "802-11-wireless-security.key-mgmt"]
        # A line per key, except key-mgmt (last): no line at all when the Wi-Fi has no security, so it's open.
        values = nmcli("-g", ",".join(keys), "connection", "show", "uuid", n.uuid)
        if not values or len(values) < len(keys) - (n.kind == "Wi-Fi"):
            continue
        got = dict(zip(keys, (v.strip() for v in values)))
        if got["ipv4.method"] == "shared" or got.get("802-11-wireless.mode") == "ap":
            continue
        n.zone = got["connection.zone"]
        n.secured = got.get("802-11-wireless-security.key-mgmt", "") not in OPEN
        out.append(n)
    return sorted(out, key=lambda n: (not n.device, n.name.lower()))


def set_place(network, zone):
    """Save the place in the network's profile. "now": saved and in effect; "later": saved, in effect from the
    next time it connects; "": not saved."""
    if zone not in PLACES or (network.fixed_public and zone != PUBLIC):
        return ""
    if nmcli("connection", "modify", "uuid", network.uuid, "connection.zone", zone) is None:
        return ""
    if network.device and nmcli("device", "reapply", network.device) is None:
        return "later"
    return "now"


def firewall(*args):
    """A firewall question any user may ask (the zone's settings, the default zone); None when it can't answer."""
    try:
        r = subprocess.run(["firewall-cmd", *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def default_zone():
    return firewall("--get-default-zone")


def running(service):
    """Whether the SSH server is switched on, or printers here are shared; None when it can't be told."""
    cmd = (["systemctl", "is-enabled", "sshd.service"] if service == "ssh" else ["cupsctl"])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if service == "ssh":
        return r.stdout.strip() == "enabled"
    return None if r.returncode != 0 else "_share_printers=1" in r.stdout.split()


def let_in(zone):
    """The system services a zone lets in, as a set; None when the firewall can't be asked."""
    out = firewall(f"--zone={zone}", "--list-services")
    return None if out is None else set(out.split())
