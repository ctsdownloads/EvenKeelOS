#!/usr/bin/python3 -I
"""Build check for Network safety: a new network is a Public place that lets nothing in, Home and Work keep apps
reachable, SSH starts off everywhere, open Wi-Fi can't be made Home, and the question is asked only where it should
be.

Usage: check-network.py   (in the image, after build.sh has set the firewall up)
"""
import subprocess
import sys

sys.path.insert(0, "/usr/lib/evenkeel-os")
import evenkeel_os_network as net  # noqa: E402

problems = []


def offline(*args):
    r = subprocess.run(["firewall-offline-cmd", *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else f"ERROR {r.stderr.strip()}"


if offline("--get-default-zone") != net.PUBLIC:
    problems.append(f"the default zone is {offline('--get-default-zone')}, not {net.PUBLIC}")
want = {net.PUBLIC: ({"mdns", "dhcpv6-client"}, set()),
        net.HOME: ({"mdns", "samba-client", "dhcpv6-client"}, {"1025-65535/tcp", "1025-65535/udp"}),
        net.WORK: ({"mdns", "samba-client", "dhcpv6-client"}, {"1025-65535/tcp", "1025-65535/udp"})}
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

if problems:
    print("ERROR: Network safety is not set up right:", *problems, sep="\n  ")
    sys.exit(1)
print("Network safety: new networks are a Public place, Home and Work keep apps reachable, SSH off, "
      f"{len(cases)} question cases right")
