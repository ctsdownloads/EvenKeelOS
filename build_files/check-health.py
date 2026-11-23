#!/usr/bin/python3
"""Build check: the trial check (evenkeel_os_health) against a made-up computer, working and then broken.

Each case changes one thing from a working computer and says whether the check must call it broken. Unplugged,
switched-off and removed things must never count, so a new version is never rolled back for them.
Usage: check-health.py [FOLDER WITH evenkeel_os_health.py]   (default: /usr/lib/evenkeel-os)
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else "/usr/lib/evenkeel-os")
import evenkeel_os_health as health  # noqa: E402

PCI = "sys/devices/pci0000:00"


class Computer:
    """A made-up computer: sysfs files and links, and the answers its programs give."""

    def __init__(self, root):
        self.root = Path(root)
        self.answers = {}
        self.cmdline = "root=x rhgb quiet"
        self.build()

    def file(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def link(self, path, target):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.is_symlink():
            p.unlink()
        p.symlink_to(os.path.relpath(self.root / target, p.parent))

    def device(self, path, bus, **files):
        self.link(f"{path}/subsystem", f"sys/bus/{bus}")
        for k, v in files.items():
            self.file(f"{path}/{k}", v)

    def driver(self, path, bus, name, builtin=False):
        self.link(f"{path}/driver", f"sys/bus/{bus}/drivers/{name}")
        self.link(f"sys/bus/{bus}/drivers/{name}/module", f"sys/module/{name}")
        if not builtin:
            self.file(f"sys/module/{name}/initstate", "live")

    def pci(self, addr, vendor, dev, drv, builtin=False):
        path = f"{PCI}/{addr}"
        self.device(path, "pci", vendor=vendor, device=dev)
        self.link(f"sys/bus/pci/devices/{addr}", path)
        if drv:
            self.driver(path, "pci", drv, builtin)
        return path

    def usb(self, name, vid, pid, removable, drv):
        path = f"{PCI}/0000:00:14.0/usb3/{name}"
        self.device(path, "usb", idVendor=vid, idProduct=pid, removable=removable)
        self.link(f"sys/bus/usb/devices/{name}", path)
        intf = f"{path}/{name}:1.0"
        self.device(intf, "usb")
        self.link(f"sys/bus/usb/devices/{name}:1.0", intf)
        if drv:
            self.driver(intf, "usb", drv)
        return intf

    def build(self):
        self.pci("0000:00:14.0", "0x8086", "0xa0ed", "xhci_hcd")
        self.file("sys/class/dmi/id/product_uuid", "abc-123")
        self.file("proc/uptime", "500.0 100.0")
        # Sound (SOF: the card hangs off a machine-driver device under the PCI audio device)
        audio = self.pci("0000:00:1f.3", "0x8086", "0xa0c8", "snd_hda_intel")
        self.device(f"{audio}/sof_sdw", "platform")
        self.link("sys/class/sound/card0", f"{audio}/sof_sdw/sound/card0")
        self.link(f"{audio}/sof_sdw/sound/card0/device", f"{audio}/sof_sdw")
        self.driver(f"{audio}/sof_sdw", "platform", "snd_soc_sof_sdw")
        # Wi-Fi and wired network
        wifi = self.pci("0000:01:00.0", "0x8086", "0x2725", "iwlwifi")
        self.link("sys/class/net/wlp1s0", f"{wifi}/net/wlp1s0")
        self.link(f"{wifi}/net/wlp1s0/device", wifi)
        self.file(f"{wifi}/net/wlp1s0/phy80211/name", "phy0")
        eth = self.pci("0000:02:00.0", "0x10ec", "0x8168", "r8169")
        self.link("sys/class/net/enp2s0", f"{eth}/net/enp2s0")
        self.link(f"{eth}/net/enp2s0/device", eth)
        self.file(f"{eth}/net/enp2s0/type", "1")
        # Bluetooth on an internal USB port, and a USB stick-style dongle in a removable port
        bt = self.usb("3-10", "8087", "0033", "fixed", "btusb")
        self.link("sys/class/bluetooth/hci0", f"{bt}/bluetooth/hci0")
        self.link(f"{bt}/bluetooth/hci0/device", bt)
        dongle = self.usb("3-1", "0a12", "0001", "removable", "btusb")
        self.link("sys/class/bluetooth/hci1", f"{dongle}/bluetooth/hci1")
        self.link(f"{dongle}/bluetooth/hci1/device", dongle)
        # Graphics
        gpu = self.pci("0000:00:02.0", "0x8086", "0x46a6", "i915")
        self.link("sys/class/drm/card1", f"{gpu}/drm/card1")
        self.link(f"{gpu}/drm/card1/device", gpu)
        # Camera on an internal USB port
        cam = self.usb("3-9", "0bda", "5634", "fixed", "uvcvideo")
        self.link("sys/class/video4linux/video0", f"{cam}/video4linux/video0")
        self.link(f"{cam}/video4linux/video0/device", cam)
        self.file(f"{cam}/video4linux/video0/name", "Laptop Camera")
        # Keyboard on the built-in keyboard port, touchpad on I2C under the PCI I2C controller
        self.device("sys/devices/platform/i8042", "platform")
        self.device("sys/devices/platform/i8042/serio0", "serio")
        kb = "sys/devices/platform/i8042/serio0/input/input3"
        self.device(kb, "input", name="AT Translated Set 2 keyboard")
        self.link(f"{kb}/device", "sys/devices/platform/i8042/serio0")
        self.link("sys/class/input/input3", kb)
        for k, v in {"bustype": "0011", "vendor": "0001", "product": "0001"}.items():
            self.file(f"{kb}/id/{k}", v)
        i2c = self.pci("0000:00:15.0", "0x8086", "0xa0e8", "intel_lpss_pci")
        self.device(f"{i2c}/i2c-1/i2c-PNP0C50:00", "i2c")
        self.device("sys/devices/LNXSYSTM:00/LNXSYBUS:00/PNP0C50:00", "acpi", status="15")
        self.link(f"{i2c}/i2c-1/i2c-PNP0C50:00/firmware_node", "sys/devices/LNXSYSTM:00/LNXSYBUS:00/PNP0C50:00")
        tp = f"{i2c}/i2c-1/i2c-PNP0C50:00/0018:093A:0274.0001/input/input5"
        self.device(tp, "input", name="PIXA3854:00 093A:0274 Touchpad")
        self.link(f"{tp}/device", f"{i2c}/i2c-1/i2c-PNP0C50:00/0018:093A:0274.0001")
        self.device(f"{i2c}/i2c-1/i2c-PNP0C50:00/0018:093A:0274.0001", "hid")
        self.link("sys/class/input/input5", tp)
        for k, v in {"bustype": "0018", "vendor": "093a", "product": "0274"}.items():
            self.file(f"{tp}/id/{k}", v)
        self.answers["udevadm /sys/class/input/input3"] = "ID_INPUT=1\nID_INPUT_KEYBOARD=1\n"
        self.answers["udevadm /sys/class/input/input5"] = "ID_INPUT=1\nID_INPUT_TOUCHPAD=1\n"
        # Battery (ACPI), backlight, Thunderbolt
        acpi = "sys/devices/LNXSYSTM:00/LNXSYBUS:00/PNP0C0A:00"
        self.device(acpi, "acpi", status="31")
        self.link("sys/class/power_supply/BAT1", f"{acpi}/power_supply/BAT1")
        self.link(f"{acpi}/power_supply/BAT1/device", acpi)
        self.file(f"{acpi}/power_supply/BAT1/type", "Battery")
        self.file(f"{acpi}/power_supply/BAT1/scope", "System")
        self.link("sys/class/backlight/intel_backlight", f"{gpu}/drm/card1/card1-eDP-1/intel_backlight")
        self.file(f"{gpu}/drm/card1/card1-eDP-1/intel_backlight/type", "raw")
        nhi = self.pci("0000:00:0d.2", "0x8086", "0x9a1b", "thunderbolt")
        self.device(f"{nhi}/domain0", "thunderbolt")
        self.link("sys/bus/thunderbolt/devices/domain0", f"{nhi}/domain0")
        # Fingerprint reader on an internal USB port, in libfprint's list
        self.usb("3-4", "27c6", "609c", "fixed", "usbfs")       # usbfs: claimed by fprintd while it runs
        self.file("usr/lib/udev/hwdb.d/60-autosuspend-fingerprint-reader.hwdb",
                  "# Supported by libfprint driver goodixmoc\nusb:v27C6p609C*\n ID_AUTOSUSPEND=1\n\n"
                  "# Known unsupported devices\nusb:v1111p2222*\n ID_AUTOSUSPEND=1\n")
        self.file("sys/fs/selinux/enforce", "1")
        self.file("proc/acpi/button/lid/LID0/state", "state:      open")
        for n in ("7", "14"):
            self.file(f"sys/class/tpm/tpm0/pcr-sha256/{n}", f"PCR{n}VALUE")
        # A USB webcam on a dock: the dock's ports aren't marked, so it's a plug-in, not listed
        self.usb("3-2.1", "046d", "085e", "unknown", "uvcvideo")
        self.file("etc/samba/evenkeel-shares.conf", "# Written by System Tools\n\n[Music]\n\tpath = /x\n")
        self.file("var/lib/evenkeel-os/disk-unlock-on", "TPM2 unlock enrolled\n")
        self.cmdline += " rd.luks.uuid=luks-0000 amdgpu.abmlevel=0"
        self.file("var/lib/evenkeel-os/boot-options.json", json.dumps({"options": ["amdgpu.abmlevel=0"]}))
        self.file("etc/evenkeel-os/shared-folders.json", json.dumps({"on": True, "folders": [{"name": "Music"}]}))
        self.answers.update({
            "lpstat -r": (0, "scheduler is running\n"),
            "power": (0, 's "balanced"\n'), "uupd": (0, "uupd version 1.0\n"), "rpm-ostree": (0, "{}"),
            "flatpak": (0, "flathub\n"), "fwupd": (0, 's "2.0.1"\n'), "firewall-cmd --state": (0, "running\n"),
            "firewall-cmd --get-zones": (0, "block evenkeel-home evenkeel-public evenkeel-work public\n"),
            "chronyd": (0, "active\n"), "resolvectl": (0, "localhost: 127.0.0.1\n"), "smb.service": (0, "active\n"),
            "testparm": (0, "[global]\n[Music]\n"), "cryptsetup log": (0, "Set cipher aes\n"),
            "kernel log": (0, "Linux version 6.17\nring gfx timeout, but soft recovered\n"),
            "fprint": (0, 'ao 1 "/net/reactivated/Fprint/Device/0"\n'),
            "running": (0, "NetworkManager.service loaded active running Network Manager\n"
                           "ModemManager.service loaded active running Modem Manager\n"),
            "failed": (0, ""), "disabled": set()})

    def run(self, cmd, timeout=30):
        a = self.answers
        joined = " ".join(cmd)
        if cmd[0] == "udevadm":
            return 0, a.get(f"udevadm {cmd[-1].split('=', 1)[1]}", "")
        if cmd[:2] == ["systemctl", "is-enabled"]:
            return (1, "disabled\n") if cmd[2] in a["disabled"] else (0, "enabled\n")
        if cmd[:2] == ["systemctl", "is-active"]:
            return a["chronyd" if "chronyd" in cmd[2] else "smb.service"]
        if cmd[:2] == ["systemctl", "list-units"]:
            return a["running" if "--state=running" in cmd else "failed"]
        if cmd[0] == "journalctl":
            return a["kernel log" if "-k" in cmd else "cryptsetup log"]
        if cmd[0] == "busctl":
            return a["fprint" if "net.reactivated.Fprint" in cmd else "power" if "ActiveProfile" in cmd else "fwupd"]
        for key in ("lpstat -r", "firewall-cmd --state", "firewall-cmd --get-zones"):
            if joined.startswith(key):
                return a[key]
        return a[cmd[0]]

    def remove(self, path):
        p = self.root / path
        if p.is_symlink() or p.is_file():
            p.unlink()
        else:
            shutil.rmtree(p)


def setup():
    d = tempfile.mkdtemp()
    c = Computer(d)
    health.ROOT = Path(d)
    health.run = c.run
    (Path(d) / "proc").mkdir(exist_ok=True)
    return c


def cmdline(c):
    c.file("proc/cmdline", c.cmdline)


def case(title, change, broken, must=None):
    """A working computer is recorded, `change` breaks (or removes) something, then the check runs."""
    c = setup()
    cmdline(c)
    health.record(0)
    change(c)
    cmdline(c)
    found = health.lost(health.load())
    names = [n for _, n in found]
    keys = [k for k, _ in found]
    if bool(found) != broken or (must and not any(must in k for k in keys)):
        sys.exit(f"ERROR: trial check, {title}: found {names or 'nothing'}, expected "
                 f"{'something broken' + (' (' + must + ')' if must else '') if broken else 'nothing'}")
    shutil.rmtree(c.root)
    return names


def main():
    c = setup()
    cmdline(c)
    health.record(0)
    rec = health.load()
    want = {"sound:pci:0000:00:1f.3", "wifi:pci:0000:01:00.0", "wired:pci:0000:02:00.0", "bluetooth:usb:8087:0033",
            "graphics:pci:0000:00:02.0", "camera:usb:0bda:5634", "keyboard:0011:0001:0001",
            "touchpad", "battery:acpi:PNP0C0A:00", "backlight", "thunderbolt:pci:0000:00:0d.2",
            "fingerprint", "printing", "power-modes", "update-program", "flatpak", "firmware-updater", "firewall",
            "network-places", "selinux", "clock-sync", "dns", "disk-unlock", "boot-options",
            "shared-folders", "service:ModemManager.service", "driver:pci:0000:00:1f.3", "driver:usb:8087:0033:1.0"}
    if want - set(rec["items"]):
        sys.exit(f"ERROR: trial check: a working made-up computer's record lacks {sorted(want - set(rec['items']))}")
    if any("0a12:0001" in k or "046d:085e" in k for k in rec["items"]):
        sys.exit("ERROR: trial check: a USB device in a removable or unmarked (hub or dock) port was recorded")
    if health.lost(rec):
        sys.exit(f"ERROR: trial check: an unchanged computer counts as broken: {health.lost(rec)}")
    # compare: exit codes, the note's file, and the cases where there's nothing to compare
    if health.compare(0) != 0 or (c.root / "var/lib/evenkeel-os/health-lost").exists():
        sys.exit("ERROR: trial check: an unchanged computer fails compare, or leaves a note")
    c.remove("sys/class/sound/card0")
    if health.compare(0) != 1 or (c.root / "var/lib/evenkeel-os/health-lost").exists():
        sys.exit("ERROR: trial check: lost sound doesn't fail a check by hand, or that leaves a list for the note")
    if health.compare(1) != 1 or "Sound" not in (c.root / "var/lib/evenkeel-os/health-lost").read_text():
        sys.exit("ERROR: trial check: lost sound doesn't fail the trial, or isn't in the note")
    if health.compare(0, "/var/lib/evenkeel-os/none.json") != 0:
        sys.exit("ERROR: trial check: no saved list fails compare")
    c.file("sys/class/dmi/id/product_uuid", "other-computer")
    if health.compare(0) != 0:
        sys.exit("ERROR: trial check: a list from another computer fails compare")
    shutil.rmtree(c.root)

    pci = f"{PCI}/0000:01:00.0"
    cases = [
        ("sound driver gone", lambda c: c.remove("sys/class/sound/card0"), True, "sound:"),
        ("sound driver blocked", lambda c: (c.remove("sys/class/sound/card0"), c.remove(f"{PCI}/0000:00:1f.3/driver"),
                                            c.remove(f"{PCI}/0000:00:1f.3/sof_sdw")), True, "sound:"),
        ("Wi-Fi driver gone", lambda c: (c.remove("sys/class/net/wlp1s0"), c.remove(f"{pci}/driver")), True, "wifi:"),
        ("Wi-Fi card switched off in the BIOS", lambda c: (c.remove("sys/class/net/wlp1s0"), c.remove(pci),
                                                           c.remove("sys/bus/pci/devices/0000:01:00.0")), False),
        ("another card in the Wi-Fi card's slot", lambda c: (c.remove("sys/class/net/wlp1s0"),
                                                             c.file(f"{pci}/device", "0x1234")), False),
        ("Wi-Fi switched off (airplane mode keeps the card)", lambda c: None, False),
        ("wired network driver gone", lambda c: c.remove("sys/class/net/enp2s0"), True, "wired:"),
        ("Bluetooth driver gone", lambda c: (c.remove("sys/class/bluetooth/hci0"),
                                             c.remove(f"{PCI}/0000:00:14.0/usb3/3-10/3-10:1.0/driver")), True,
         "bluetooth:"),
        ("removable Bluetooth dongle unplugged", lambda c: (c.remove("sys/class/bluetooth/hci1"),
                                                            c.remove(f"{PCI}/0000:00:14.0/usb3/3-1"),
                                                            c.remove("sys/bus/usb/devices/3-1"),
                                                            c.remove("sys/bus/usb/devices/3-1:1.0")), False),
        ("internal Bluetooth found under a new USB number", move_bluetooth, False),
        ("graphics driver gone", lambda c: (c.remove("sys/class/drm/card1"), c.remove(f"{PCI}/0000:00:02.0/driver")),
         True, "graphics:"),
        ("camera driver gone", lambda c: c.remove("sys/class/video4linux/video0"), True, "camera:"),
        ("camera privacy switch (the camera leaves USB)", lambda c: (c.remove("sys/class/video4linux/video0"),
                                                                     c.remove(f"{PCI}/0000:00:14.0/usb3/3-9"),
                                                                     c.remove("sys/bus/usb/devices/3-9"),
                                                                     c.remove("sys/bus/usb/devices/3-9:1.0")), False),
        ("keyboard driver gone", lambda c: c.remove("sys/class/input/input3"), True, "keyboard:"),
        ("touchpad driver gone", lambda c: c.remove("sys/class/input/input5"), True, "touchpad"),
        ("touchpad moved to another driver by a new kernel", move_touchpad, False),
        ("keyboard controller gone with its keyboard", lambda c: (c.remove("sys/class/input/input3"),
                                                                  c.remove("sys/devices/platform/i8042")), False),
        ("touchpad switched off in the BIOS", lambda c: (
            c.remove("sys/class/input/input5"), c.remove(f"{PCI}/0000:00:15.0/i2c-1/i2c-PNP0C50:00"),
            c.file("sys/devices/LNXSYSTM:00/LNXSYBUS:00/PNP0C50:00/status", "0")), False),
        ("battery driver gone", lambda c: c.remove("sys/class/power_supply/BAT1"), True, "battery:"),
        ("battery taken out", lambda c: (c.remove("sys/class/power_supply/BAT1"),
                                         c.file("sys/devices/LNXSYSTM:00/LNXSYBUS:00/PNP0C0A:00/status", "15")),
         False),
        ("brightness control gone", lambda c: c.remove("sys/class/backlight/intel_backlight"), True, "backlight"),
        ("brightness control gone with the lid closed", lambda c: (
            c.remove("sys/class/backlight/intel_backlight"),
            c.file("proc/acpi/button/lid/LID0/state", "state:      closed")), False),
        ("Thunderbolt driver gone", lambda c: c.remove("sys/bus/thunderbolt/devices/domain0"), True, "thunderbolt"),
        ("fingerprint reader not found by fprintd", lambda c: c.answers.update(fprint=(0, "ao 0\n")), True,
         "fingerprint"),
        ("fingerprint reader unplugged", lambda c: (c.answers.update(fprint=(0, "ao 0\n")),
                                                    c.remove(f"{PCI}/0000:00:14.0/usb3/3-4"),
                                                    c.remove("sys/bus/usb/devices/3-4"),
                                                    c.remove("sys/bus/usb/devices/3-4:1.0")), False),
        ("fingerprint reader let go by fprintd", lambda c: c.remove(f"{PCI}/0000:00:14.0/usb3/3-4/3-4:1.0/driver"),
         False),
        ("a device handed to a virtual machine", lambda c: (c.driver(f"{PCI}/0000:02:00.0", "pci", "vfio-pci"),
                                                            c.remove("sys/class/net/enp2s0")), False),
        ("printing broken", lambda c: c.answers.update({"lpstat -r": (1, "scheduler is not running\n")}), True,
         "printing"),
        ("printing switched off by its owner", printing_off, False),
        ("power modes broken", lambda c: c.answers.update(power=(1, "")), True, "power-modes"),
        ("update program broken", lambda c: c.answers.update(uupd=(1, "")), True, "update-program"),
        ("Flatpak broken", lambda c: c.answers.update(flatpak=(1, "")), True, "flatpak"),
        ("firmware updater broken", lambda c: c.answers.update(fwupd=(1, "")), True, "firmware-updater"),
        ("firewall broken", lambda c: c.answers.update({"firewall-cmd --state": (252, "not running\n")}), True,
         "firewall"),
        ("network places gone", lambda c: c.answers.update({"firewall-cmd --get-zones": (0, "public\n")}), True,
         "network-places"),
        ("SELinux off", lambda c: c.file("sys/fs/selinux/enforce", "0"), True, "selinux"),
        ("clock sync broken", lambda c: c.answers.update(chronyd=(3, "failed\n")), True, "clock-sync"),
        ("DNS broken", lambda c: c.answers.update(resolvectl=(1, "")), True, "dns"),
        ("disk unlock asked for the password", lambda c: c.answers.update(
            {"cryptsetup log": (0, "TPM2 operation failed, falling back to traditional unlocking: x\n")}), True,
         "disk-unlock"),
        ("disk unlock failed after a firmware change", lambda c: (c.answers.update(
            {"cryptsetup log": (0, "TPM2 operation failed, falling back to traditional unlocking: x\n")}),
            c.file("sys/class/tpm/tpm0/pcr-sha256/7", "NEWVALUE")), False),
        ("disk unlock switched off by its owner", lambda c: (c.answers.update(
            {"cryptsetup log": (0, "No TPM2 metadata enrolled in LUKS2 header, falling back to traditional "
                                   "unlocking.\n")}), c.remove("var/lib/evenkeel-os/disk-unlock-on")), False),
        ("Boot options setting dropped", lambda c: setattr(c, "cmdline", c.cmdline.replace(" amdgpu.abmlevel=0", "")),
         True, "boot-options"),
        ("Boot options all taken out by their owner", lambda c: (
            setattr(c, "cmdline", c.cmdline.replace(" amdgpu.abmlevel=0", "")),
            c.file("var/lib/evenkeel-os/boot-options.json", json.dumps({"options": []}))), False),
        ("Shared folders missing from Samba's settings", lambda c: c.answers.update(testparm=(0, "[global]\n")),
         True, "shared-folders"),
        ("Shared folders away from a Home network (Samba stopped)",
         lambda c: c.answers.update({"smb.service": (3, "inactive\n")}), False),
        ("a shared folder added with no sharing password yet", lambda c: c.file(
            "etc/evenkeel-os/shared-folders.json", json.dumps({"on": True, "folders": [{"name": "Music"},
                                                                                       {"name": "Photos"}]})), False),
        ("Shared folders switched off by their owner", lambda c: c.file("etc/evenkeel-os/shared-folders.json",
                                                                        json.dumps({"on": False})), False),
        ("a running service failed", lambda c: c.answers.update(failed=(0, "ModemManager.service loaded failed failed"
                                                                           " Modem Manager\n")), True, "service:"),
        ("a running service failed (shown with a dot)", lambda c: c.answers.update(
            failed=(0, "\u25cf ModemManager.service loaded failed failed Modem Manager\n")), True, "service:"),
        ("a running service stopped (not failed)", lambda c: c.answers.update(
            running=(0, "NetworkManager.service loaded active running Network Manager\n")), False),
        ("a one-time job failed offline", lambda c: c.answers.update(
            failed=(0, "NetworkManager-wait-online.service loaded failed failed Wait\n")), False),
        ("a new kernel crash", lambda c: c.answers.update({"kernel log": (0, "Oops: general protection fault, "
                                                                              "probably for address\n")}), True,
         "crash:oops"),
        ("an app's own protection fault", lambda c: c.answers.update(
            {"kernel log": (0, "traps: wine64[4242] general protection fault ip:7f sp:7f error:0\n")}), False),
        ("a GPU hang (often one app's)", lambda c: c.answers.update(
            {"kernel log": (0, "i915 0000:00:02.0: [drm] GPU HANG: ecode 12, in game [99]\n")}), False),
        ("boot options changed: graphics and SELinux off on purpose", options_change, False),
        ("boot options changed while an update waited", options_with_update, False),
        ("boot options changed and printing broke", lambda c: (options_change(c), c.answers.update(
            {"lpstat -r": (1, "scheduler is not running\n")})), True, "printing"),
        ("a GPU timeout it recovered from", lambda c: c.answers.update(
            {"kernel log": (0, "amdgpu: ring gfx_0.0.0 timeout, but soft recovered\n")}), False),
        ("offline (no network at all)", lambda c: None, False),
    ]
    for args in cases:
        case(*args)
    crash_seen_before()
    own_mistake()
    test_args()
    print(f"Trial check: {len(want)} kinds of things recorded; {len(cases)} changes, each counted or not as it "
          "should be; test copies get the right driver blocks")


def options_change(c):
    """The same version with other boot options (System Tools, Boot options): nomodeset and selinux=0."""
    c.answers["rpm-ostree"] = (0, json.dumps({"deployments": [{"booted": True, "checksum": "aaa"},
                                                                  {"booted": False, "checksum": "aaa"}]}))
    c.remove("sys/class/drm/card1")
    c.remove(f"{PCI}/0000:00:02.0/driver")
    c.remove("sys/class/backlight/intel_backlight")
    c.file("sys/fs/selinux/enforce", "0")


def options_with_update(c):
    """A Boot options change (nomodeset) made while an update was waiting: the start is the update's trial."""
    setattr(c, "cmdline", c.cmdline + " nomodeset")
    c.remove("sys/class/drm/card1")
    c.remove(f"{PCI}/0000:00:02.0/driver")
    c.remove("sys/class/backlight/intel_backlight")


def move_touchpad(c):
    """A new kernel moves the touchpad from the I2C bus to the PS/2 port's SMBus driver: new bus, new name."""
    c.remove("sys/class/input/input5")
    tp = "sys/devices/platform/i8042/serio1/rmi4-00/input/input9"
    c.device("sys/devices/platform/i8042/serio1", "serio")
    c.device(tp, "input", name="Synaptics TM3562-003")
    c.link(f"{tp}/device", "sys/devices/platform/i8042/serio1/rmi4-00")
    c.link("sys/class/input/input9", tp)
    for k, v in {"bustype": "001d", "vendor": "06cb", "product": "0000"}.items():
        c.file(f"{tp}/id/{k}", v)
    c.answers["udevadm /sys/class/input/input9"] = "ID_INPUT=1\nID_INPUT_TOUCHPAD=1\n"


def printing_off(c):
    c.answers["lpstat -r"] = (1, "scheduler is not running\n")
    c.answers["disabled"].update({"cups.socket", "cups.service"})


def move_bluetooth(c):
    """The same internal Bluetooth found under another USB number after a restart."""
    c.remove(f"{PCI}/0000:00:14.0/usb3/3-10")
    for n in ("3-10", "3-10:1.0"):
        c.remove(f"sys/bus/usb/devices/{n}")
    c.remove("sys/class/bluetooth/hci0")
    bt = c.usb("1-10", "8087", "0033", "fixed", "btusb")
    c.link("sys/class/bluetooth/hci0", f"{bt}/bluetooth/hci0")
    c.link(f"{bt}/bluetooth/hci0/device", bt)


def own_mistake():
    """A mistake in the check itself must not fail the start."""
    c = setup()
    cmdline(c)
    health.record(0)

    def broken(cmd, timeout=30):
        raise RuntimeError("made-up mistake")
    health.run = broken
    if health.compare(0) != 0:
        sys.exit("ERROR: trial check: a mistake in the check fails the start")
    shutil.rmtree(c.root)


def crash_seen_before():
    c = setup()
    c.answers["kernel log"] = (0, "BUG: kernel NULL pointer dereference, address: 0\n")
    cmdline(c)
    health.record(0)
    if health.lost(health.load()):
        sys.exit("ERROR: trial check: a crash kind already seen at the last good start counts as new")
    shutil.rmtree(c.root)


def test_args():
    c = setup()
    if health.test_args("sound") != 7:
        sys.exit("ERROR: trial check: a test runs with no saved list of what works")
    if health.test_args("quick") != []:
        sys.exit("ERROR: trial check: the first six rollback tests need a saved list of what works")
    # A second sound card on the same chip with its own driver: both are blocked.
    audio = f"{PCI}/0000:00:1f.3"
    c.device(f"{audio}/hdmi", "platform")
    c.link("sys/class/sound/card2", f"{audio}/hdmi/sound/card2")
    c.link(f"{audio}/hdmi/sound/card2/device", f"{audio}/hdmi")
    c.driver(f"{audio}/hdmi", "platform", "snd_hda_codec_hdmi")
    cmdline(c)
    health.record(0)
    got = {k: health.test_args(k) for k in ("sound", "wifi", "bluetooth", "graphics", "printing", "service")}
    want = {"sound": ["module_blacklist=snd_hda_codec_hdmi,snd_soc_sof_sdw"], "wifi": ["module_blacklist=iwlwifi"],
            "bluetooth": ["module_blacklist=btusb"], "graphics": ["module_blacklist=i915"], "printing": [],
            "service": []}
    if got != want:
        sys.exit(f"ERROR: trial check: test copies would block {got}, not {want}")
    c.cmdline += " module_blacklist=nouveau"       # the owner's own block stays in the test copy's
    cmdline(c)
    if health.test_args("graphics") != ["module_blacklist=nouveau,i915"]:
        sys.exit(f"ERROR: trial check: the owner's own driver block is dropped: {health.test_args('graphics')}")
    c.remove("sys/module/i915/initstate")         # built into the system: can't be blocked
    if health.test_args("graphics") != 9:
        sys.exit("ERROR: trial check: a built-in graphics driver isn't refused")
    c.answers["running"] = (0, "")
    c.answers["lpstat -r"] = (1, "scheduler is not running\n")
    c.remove("sys/class/net/wlp1s0")
    health.record(0)
    for kind in ("wifi", "printing", "service"):
        if health.test_args(kind) != 8:
            sys.exit(f"ERROR: trial check: the {kind} test runs on a computer without it working")
    shutil.rmtree(c.root)


if __name__ == "__main__":
    main()
