#!/usr/bin/python3 -I
"""Build test for Install Package File: read four real Fedora packages and check what it says they need."""
import json
import subprocess
import sys
from pathlib import Path

folder = Path(sys.argv[1])
problems = []


def expect(ok, problem):
    if not ok:
        problems.append(problem)


def check(name):
    f = next(folder.glob(f"{name}-[0-9]*.rpm"))
    out = subprocess.run(["python3", "-I", "/usr/bin/evenkeel-os-packages", "check", str(f)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


mines = check("gnome-mines")
expect(mines["apps"] and not mines["needs_system"], f"gnome-mines should go in a box: {mines}")
vpn = check("openvpn")
expect("a background service that starts with the computer" in vpn["needs_system"], f"openvpn: {vpn}")
rules = check("solaar-udev")
expect(rules["rules_only"] and rules["rules"], f"solaar-udev should be a hardware rule only: {rules}")
source = check("fedora-repos-archive")
expect(source["source_only"] and source["sources"] and not source["apps"],
       f"fedora-repos-archive only adds a download source: {source}")
if problems:
    sys.exit("ERROR: Install Package File misreads packages:\n  - " + "\n  - ".join(problems))
print("Install Package File reads packages correctly")
