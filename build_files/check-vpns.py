#!/usr/bin/python3 -I
"""Build check for Get a VPN: every VPN is complete, its signing key is the pinned one, its download source file
is right, and the helper finds the services real install scripts turn on.

Runs in the image build, against the installed list, keys and helper. Changes nothing on the system.
"""
import importlib.machinery
import importlib.util
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

LIST = Path("/usr/share/evenkeel-os/vpns.json")
KEYS = Path("/usr/share/evenkeel-os/vpn-keys")
NAME = re.compile(r"^[a-z0-9-]+$")
PKG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+_-]{0,127}$")
UNIT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,127}\.(service|socket|timer|path)$")
problems, warnings = [], []
fedora = platform.freedesktop_os_release()["VERSION_ID"]

loader = importlib.machinery.SourceFileLoader("vpnhelper", "/usr/libexec/evenkeel-os-vpn")
helper = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(helper)

vpns = json.loads(LIST.read_text())
for name, v in vpns.items():
    if not NAME.match(name):
        problems.append(f"{name}: not a usable name")
    for field in ("title", "maker", "packages", "files", "keys", "repos", "enable"):
        if not v.get(field):
            problems.append(f"{name}: no {field}")
    if not all(PKG.match(p) for p in v.get("packages", []) + v.get("files", [])):
        problems.append(f"{name}: a package name has characters that aren't allowed")
    if not all(UNIT.match(u) for u in v.get("enable", []) + list(v.get("copy_units", {}))):
        problems.append(f"{name}: a service name has characters that aren't allowed")
    if not set(v.get("start", [])) <= set(v.get("enable", [])):
        problems.append(f"{name}: a service is started but never turned on")
    if not all(src.startswith("/usr/share/") for src in v.get("copy_units", {}).values()):
        problems.append(f"{name}: a service file is copied from outside /usr/share")
    for version, key in v.get("keys", {}).items():
        out = subprocess.run(["gpg", "--batch", "--show-keys", "--with-colons", str(KEYS / key["file"])],
                             capture_output=True, text=True).stdout
        first = next((line.split(":")[9] for line in out.splitlines() if line.startswith("fpr:")), "")
        if first != key["fingerprint"]:
            problems.append(f"{name}: the key for Fedora {version} is not the pinned one ({first or 'unreadable'})")
    key = helper.key_for(v)
    if not key:
        warnings.append(f"{v['title']} has no signing key for Fedora {fedora}, so Get a VPN says it isn't available "
                        f"yet. Add the key from {v['repos'][0]['baseurl']}")
        continue
    text = helper.repo_text(name, v, key)
    checked = len(re.findall(r"^gpgcheck=1$", text, re.M)) == len(v["repos"])
    # a key named per Fedora version ($releasever) must name this version's pinned key file
    named = v.get("key_name", key["file"])
    if named.replace("$releasever", fedora) != key["file"]:
        problems.append(f"{name}: its key name {named} doesn't give {key['file']} on Fedora {fedora}")
    if not checked or f"gpgkey=file://{KEYS / named}\n" not in text or not text.startswith(helper.marker(name)):
        problems.append(f"{name}: its download source file doesn't check signatures with the pinned key")

# Real install scripts: Mullvad's turns on two services and starts one; NordVPN's quiet lines count too.
mullvad = '''systemctl enable "/usr/lib/systemd/system/mullvad-daemon.service"
systemctl start mullvad-daemon.service || echo "Failed to start mullvad-daemon.service"
systemctl enable "/usr/lib/systemd/system/mullvad-early-boot-blocking.service"
if ! systemctl is-enabled mullvad-daemon; then
systemctl disable mullvad-early-boot-blocking.service || true'''
got = helper.asked_for(mullvad, ["mullvad-daemon.service", "mullvad-early-boot-blocking.service"])
if got != (["mullvad-daemon.service", "mullvad-early-boot-blocking.service"], ["mullvad-daemon.service"]):
    problems.append(f"the services in Mullvad's install script were read as {got}")
nord = '''                systemctl enable nordvpnd.socket &>/dev/null || :
                systemctl start nordvpnd.service &>/dev/null || :
            sudo systemctl disable nordvpnd.service &>/dev/null || :
systemctl --user enable other.service'''
got = helper.asked_for(nord, ["nordvpnd.socket", "nordvpnd.service", "other.service"])
if got != (["nordvpnd.socket"], ["nordvpnd.service"]):
    problems.append(f"the services in NordVPN's install script were read as {got}")

for w in warnings:
    print(f"WARNING: {w}")
if problems:
    print("ERROR: Get a VPN check failed:")
    for p in problems:
        print(f"  - {p}")
    sys.exit(1)
print(f"Get a VPN: {len(vpns)} VPNs, every signing key is the pinned one and every download source checks "
      f"signatures; install scripts are read correctly")
