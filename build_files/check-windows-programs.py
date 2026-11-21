#!/usr/bin/python3 -I
"""Build test for Windows Program: the list is full, and real and made-up installers get the right offer."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

folder = Path(sys.argv[1])
programs = json.loads(Path("/usr/share/evenkeel-os/windows-apps.json").read_text())["programs"]
offers = [p["offer"] for p in programs.values()]
same = {o["flatpak"] for o in offers if o.get("flatpak") and "job" not in o}
listed = [o for o in offers if o.get("job") and not o.get("kind")]
kinds = [o for o in offers if o.get("kind")]
assert len(same) >= 500, f"only {len(same)} Flathub apps are the same program as a Windows one"
assert len(listed) >= 300, f"only {len(listed)} hand-picked replacements"
assert len(kinds) >= 1000, f"only {len(kinds)} programs get an app of the same kind"
for key, app in [("Mozilla.Firefox", "org.mozilla.firefox"), ("VideoLAN.VLC", "org.videolan.VLC"),
                 ("Zoom.Zoom", "us.zoom.Zoom"), ("GIMP.GIMP", "org.gimp.GIMP")]:
    got = programs.get(key, {}).get("offer", {}).get("flatpak")
    assert got == app, f"{key} should be {app} in the Windows programs list, not {got}"
qute = programs.get("qutebrowser.qutebrowser", {}).get("offer", {})
assert qute.get("fedora") == "qutebrowser" and qute.get("ubuntu") == "qutebrowser", \
    f"qutebrowser should be matched to Fedora's and Ubuntu's qutebrowser: {qute}"


def check(path):
    out = subprocess.run(["python3", "-I", "/usr/bin/evenkeel-os-packages", "check-windows", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def made_up_msi(name, maker, where, file_name="setup.msi"):
    """A tiny .msi that only says its name and maker, like an old installer would."""
    wxs = where / "p.wxs"
    wxs.write_text(f'<?xml version="1.0"?><Wix xmlns="http://schemas.microsoft.com/wix/2006/wi"><Product Id="*" '
                   f'Name="{name}" Manufacturer="{maker}" Version="1.0.0" Language="1033" '
                   f'UpgradeCode="11111111-2222-3333-4444-555555555555"><Package InstallerVersion="200" '
                   f'Compressed="yes"/><Directory Id="TARGETDIR" Name="SourceDir"/><Feature Id="F" Level="1"/>'
                   f'</Product></Wix>')
    msi = where / file_name
    subprocess.run(["wixl", "-o", str(msi), str(wxs)], check=True, capture_output=True)
    return check(msi)


putty = check(next(folder.glob("putty-*.msi")))
assert putty["package"] == "uk.org.greenend.chiark.sgtatham.putty" and putty["how"] == "product code", \
    f"the PuTTY .msi should offer PuTTY from Flathub: {putty}"
bitwarden = check(next(folder.glob("*Bitwarden*.exe")))
assert bitwarden["name"] and bitwarden["package"] == "com.bitwarden.desktop", \
    f"the Bitwarden .exe should offer Bitwarden from Flathub: {bitwarden}"
npp = check(next(folder.glob("npp.*.exe")))
assert npp["name"] and npp["kind"] == "replacement", f"Notepad++ should get a hand-picked replacement: {npp}"
sevenzip = check(next(folder.glob("7z*.exe")))
assert sevenzip["name"], f"the 7-Zip .exe was not read: {sevenzip}"
qb = check(next(folder.glob("qutebrowser-*.exe")))
assert qb["kind"] == "same app" and qb["package"] in ("qutebrowser", "org.qutebrowser.qutebrowser"), \
    f"the qutebrowser .exe should offer qutebrowser: {qb}"
with tempfile.TemporaryDirectory() as tmp:
    photoshop = made_up_msi("Adobe Photoshop", "Adobe Inc.", Path(tmp))
    assert photoshop["where"] == "artcraft" and photoshop["package"] == "photocraft", \
        f"Photoshop should offer ArtCraft's PhotoCraft: {photoshop}"
    zoom = made_up_msi("Zoom Workplace", "Zoom Video Communications, Inc.", Path(tmp))
    assert zoom["where"] == "web", f"Zoom should open in the browser, not install the app: {zoom}"
    reader = made_up_msi("Adobe Self Extractor", "Adobe Systems Incorporated", Path(tmp),
                         "AcroRdrDCx642600322110_en_US.msi")
    assert reader["where"] == "artcraft" and reader["package"] == "pdfcraft", \
        f"Acrobat Reader's installer (named only 'Adobe Self Extractor') should offer PdfCraft: {reader}"
    msn = made_up_msi("Windows Live Messenger", "Microsoft Corporation", Path(tmp))
    assert msn["kind"] == "replacement", f"Windows Live Messenger should get a hand-picked replacement: {msn}"
    player = made_up_msi("Zyxwv Digital Media Player", "Nobody Software", Path(tmp))
    assert player["how"] == "description" and player["package"], \
        f"an unknown media player should get a player from its own description: {player}"
print(f"Windows Program reads installers correctly; {len(same)} same apps on Flathub, {len(listed)} hand-picked "
      f"replacements, {len(kinds)} by kind")
