#!/usr/bin/python3 -I
"""Build test for Windows Program: the list is full and five real installers are read and matched right."""
import json
import subprocess
import sys
from pathlib import Path

folder = Path(sys.argv[1])
data = json.loads(Path("/usr/share/evenkeel-os/windows-apps.json").read_text())
programs = {m["flatpak"] for m in data["matches"].values() if m.get("flatpak")}
assert len(programs) >= 500, f"only {len(programs)} Linux apps in the Windows programs list"
for pid, app in [("Mozilla.Firefox", "org.mozilla.firefox"), ("VideoLAN.VLC", "org.videolan.VLC"),
                 ("Zoom.Zoom", "us.zoom.Zoom"), ("GIMP.GIMP", "org.gimp.GIMP")]:
    got = data["matches"].get(pid, {}).get("flatpak")
    assert got == app, f"{pid} should be {app} in the Windows programs list, not {got}"
qute = data["matches"].get("qutebrowser.qutebrowser", {})
assert qute.get("fedora") == "qutebrowser" and qute.get("ubuntu") == "qutebrowser", \
    f"qutebrowser should be matched to Fedora's and Ubuntu's qutebrowser: {qute}"
fedora = sum(1 for m in data["matches"].values() if m.get("fedora"))
ubuntu = sum(1 for m in data["matches"].values() if m.get("ubuntu"))
assert fedora >= 80 and ubuntu >= 60, f"too few Fedora ({fedora}) or Ubuntu ({ubuntu}) matches"


def check(name):
    f = next(folder.glob(name))
    out = subprocess.run(["python3", "-I", "/usr/bin/evenkeel-os-packages", "check-windows", str(f)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


putty = check("putty-*.msi")
assert putty["package"] == "uk.org.greenend.chiark.sgtatham.putty" and putty["how"] == "product code", \
    f"the PuTTY .msi should offer PuTTY from Flathub: {putty}"
bitwarden = check("*Bitwarden*.exe")
assert bitwarden["name"] and bitwarden["package"] == "com.bitwarden.desktop", \
    f"the Bitwarden .exe should offer Bitwarden from Flathub: {bitwarden}"
npp = check("npp.*.exe")
assert npp["name"] and not npp["package"], f"Notepad++ has no Linux version, so nothing should be offered: {npp}"
sevenzip = check("7z*.exe")
assert sevenzip["name"], f"the 7-Zip .exe was not read: {sevenzip}"
qb = check("qutebrowser-*.exe")
assert qb["program"] == "qutebrowser.qutebrowser" and qb["where"] in ("flathub", "rpm"), \
    f"the qutebrowser .exe should offer qutebrowser: {qb}"
print(f"Windows Program reads installers correctly; {len(programs)} Flathub apps, {fedora} Fedora and {ubuntu} "
      f"Ubuntu matches in its list")
