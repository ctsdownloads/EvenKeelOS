#!/usr/bin/python3 -I
"""Build check for Network safety: zones, SSH, open Wi-Fi and Let in behave as promised."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/usr/lib/evenkeel-os")
import evenkeel_os_letin as letin  # noqa: E402
import evenkeel_os_network as net  # noqa: E402

problems = []


def offline(*args):
    r = subprocess.run(["firewall-offline-cmd", *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else f"ERROR {r.stderr.strip()}"


if offline("--get-default-zone") != net.PUBLIC:
    problems.append(f"the default zone is {offline('--get-default-zone')}, not {net.PUBLIC}")
want = {net.PUBLIC: ({"mdns", "dhcpv6-client"}, set()),
        net.HOME: ({"mdns", "samba-client", "dhcpv6-client"}, {"1025-65535/tcp", "1025-65535/udp"}),
        net.WORK: ({"mdns", "samba-client", "dhcpv6-client"}, set())}
for zone, (services, ports) in want.items():
    got_services = set(offline(f"--zone={zone}", "--list-services").split())
    got_ports = set(offline(f"--zone={zone}", "--list-ports").split())
    if got_services != services or got_ports != ports:
        problems.append(f"{zone} lets in services {sorted(got_services)} and ports {sorted(got_ports)}, "
                        f"not {sorted(services)} and {sorted(ports)}")
if set(net.PLACES) != set(want):
    problems.append(f"the places offered {sorted(net.PLACES)} aren't the zones set up {sorted(want)}")


def network(kind, device, zone="", secured=False):
    n = net.Network("00000000-0000-0000-0000-000000000000", "Test", kind, device)
    n.zone, n.secured = zone, secured
    return n


cases = [("password Wi-Fi, joined, never asked", network("Wi-Fi", "wlp1s0", secured=True), True),
         ("wired: one profile matches every cable", network("Wired", "enp2s0"), False),
         ("open Wi-Fi", network("Wi-Fi", "wlp1s0"), False),
         ("password Wi-Fi already set", network("Wi-Fi", "wlp1s0", net.HOME, True), False),
         ("password Wi-Fi not joined", network("Wi-Fi", "", secured=True), False)]
for label, n, want_ask in cases:
    if n.needs_asking != want_ask:
        problems.append(f"{label}: {'asked' if n.needs_asking else 'not asked'}")
if net.set_place(network("Wi-Fi", ""), net.HOME) or not network("Wi-Fi", "").fixed_public:
    problems.append("open Wi-Fi could be made Home")
if "owe" not in net.OPEN:
    problems.append("Enhanced Open (OWE) Wi-Fi, which has no password, would count as a password network")
if net.fields(r"id-1:802-11-wireless:Caf\:e \\ net:wlp1s0") != ["id-1", "802-11-wireless", "Caf:e \\ net", "wlp1s0"]:
    problems.append("a network name with a colon or backslash is read wrong")

# Let in: what the helper and the page accept, and what removing an entry never takes out.
for spec, want_port in (("8096/tcp", "8096/tcp"), ("2456-2458/udp", "2456-2458/udp"), ("08080/tcp", "8080/tcp"),
                        ("22/TCP", ""), ("0/tcp", ""), ("65536/udp", ""), ("10-5/tcp", ""), ("22/sctp", ""),
                        ("22", ""), ("22/tcp;id", ""), ("-1/tcp", ""), ("1e3/tcp", "")):
    if letin.port(spec) != want_port:
        problems.append(f"the port {spec!r} reads as {letin.port(spec)!r}, not {want_port!r}")
if letin.ports([]) is not None or letin.ports(["80/tcp"] * 2) is not None or \
        letin.ports([f"{n}/tcp" for n in range(1, letin.MAX_PORTS + 2)]) is not None:
    problems.append("no ports, the same port twice, or too many ports are accepted")
for text, want_label in (("  My   game ", "My game"), ("", ""), ("a\x07b", ""), ("x" * 61, "")):
    if letin.label(text) != want_label:
        problems.append(f"the name {text!r} reads as {letin.label(text)!r}, not {want_label!r}")
if letin.zone_base(net.HOME) != ({"mdns", "samba-client", "dhcpv6-client"}, {"1025-65535/tcp", "1025-65535/udp"}):
    problems.append(f"Home's own settings read as {letin.zone_base(net.HOME)}: removing an app could close them")
everything = letin.apps()
for want_app in ("Minecraft", "Jellyfin", "SSH", "ssh"):
    if not any(a["name"] == want_app for a in letin.find(want_app, everything)):
        problems.append(f"searching {want_app} doesn't find it in the app list")
if not Path("/usr/lib/systemd/system/multi-user.target.wants/evenkeel-os-work-update.service").exists():
    problems.append("the one-time Work update isn't switched on")

if problems:
    print("ERROR: Network safety is not set up right:", *problems, sep="\n  ")
    sys.exit(1)
print("Network safety: new networks are a Public place, Work lets nothing in, Home keeps apps reachable, SSH off, "
      f"{len(cases)} question cases right, Let in reads ports and names right and finds apps")
