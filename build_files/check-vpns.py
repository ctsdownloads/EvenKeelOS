#!/usr/bin/python3 -I
"""Build check for Get a VPN: each VPN is complete, with the pinned signing key and the right download source."""
import json
import platform
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/usr/lib/evenkeel-os")
from evenkeel_os_ui import load_program  # noqa: E402

NAME = re.compile(r"^[a-z0-9-]+$")
PKG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+_-]{0,127}$")
UNIT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,127}\.(service|socket|timer|path)$")
problems, warnings = [], []
fedora = platform.freedesktop_os_release()["VERSION_ID"]

helper = load_program("/usr/libexec/evenkeel-os-vpn", "vpnhelper")

vpns = json.loads(helper.LIST.read_text())
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
        out = subprocess.run(["gpg", "--batch", "--show-keys", "--with-colons", str(helper.KEYS / key["file"])],
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
    if not checked or f"gpgkey=file://{helper.KEYS / named}\n" not in text or not text.startswith(helper.marker(name)):
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

# Removal undoes the folders it made (NordVPN has one), with the system's commands stood in for.
with tempfile.TemporaryDirectory() as d:
    folder = Path(d, "made")
    folder.mkdir()
    helper.ADDED, helper.UNITS, helper.REPOS = Path(d, "added.json"), Path(d), Path(d)
    helper.note_added("folders", str(folder))
    helper.systemctl = lambda *args: True
    helper.requested = lambda booted=True: set()
    helper.remove_group = lambda group: None
    v = {"title": "Test", "packages": ["test"], "enable": [], "group": "g", "folders": [{"path": str(folder)}]}
    try:
        helper.remove("test", v)
    except Exception as e:  # noqa: BLE001
        problems.append(f"removing a VPN with a folder of its own fails: {e!r}")
    if folder.exists() or helper.added()["folders"]:
        problems.append("removing a VPN leaves the folder it made")

for w in warnings:
    print(f"WARNING: {w}")
if problems:
    print("ERROR: Get a VPN check failed:")
    for p in problems:
        print(f"  - {p}")
    sys.exit(1)
print(f"Get a VPN: {len(vpns)} VPNs, every signing key is the pinned one and every download source checks "
      f"signatures; install scripts are read correctly")
