"""The fit check on the live USB: whether this computer's parts will work with EvenKeelOS, read from the kernel.

Each result is (level, part, what it found, what to do): level is "good", "limited" or "bad".
"""
import glob
import math
import os
import re
import subprocess

SYS = "/sys"
PROC = "/proc"
GOOD, LIMITED, BAD = "good", "limited", "bad"
VENDORS = {"0x8086": "Intel", "0x1002": "AMD", "0x10de": "NVIDIA", "0x14e4": "Broadcom", "0x10ec": "Realtek",
           "0x14c3": "MediaTek", "0x168c": "Qualcomm Atheros", "0x17cb": "Qualcomm"}
BROADCOM = "0x14e4"
NO_FIRMWARE = ("b43", "b43legacy")           # Broadcom drivers whose firmware Fedora can't include
RAID_HIDDEN = re.compile(r"remapped NVMe devices|Switch your BIOS from RAID to AHCI")
EFI_GLOBAL = "8be4df61-93ca-11d2-aa0d-00e098032b8c"
MIN_DISK = 20 * 10 ** 9                      # Fedora Workstation's minimum disk
MIN_MEMORY_GB = 8                            # the README's recommended amount
TOUCHPADS = ("touchpad", "trackpad", "glidepoint", "synaptics", "bcm5974")


def read(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def pci_devices():
    """[{"slot", "class", "vendor", "driver", "path"}] for every PCI device."""
    out = []
    for path in sorted(glob.glob(f"{SYS}/bus/pci/devices/*")):
        driver = os.path.realpath(f"{path}/driver")
        out.append({"slot": os.path.basename(path), "class": read(f"{path}/class"), "vendor": read(f"{path}/vendor"),
                    "driver": os.path.basename(driver) if os.path.isdir(f"{path}/driver") else "", "path": path})
    return out


def vendor(dev):
    return VENDORS.get(dev["vendor"], "")


def kind(dev, prefix):
    """Whether the device's PCI class code (0xCCSSPP) starts with the hex digits given."""
    return dev["class"].lower().startswith("0x" + prefix)


def kernel_log():
    """This start's kernel messages, or "" when they can't be read."""
    for cmd in (["journalctl", "-k", "-b", "0", "-o", "cat", "--no-pager"], ["dmesg"]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
    return ""


def raid_hidden(log=None):
    """Whether the BIOS's RAID (Intel RST) setting hides a disk from Linux: the kernel says so, or, when its
    messages can't be read, an Intel SATA controller runs in RAID mode and no disk inside the computer shows."""
    if log is not None:
        return bool(RAID_HIDDEN.search(log))
    log = kernel_log()
    if log:
        return bool(RAID_HIDDEN.search(log))
    rst = any(d["vendor"] == "0x8086" and kind(d, "0104") and d["driver"] == "ahci" for d in pci_devices())
    return rst and not internal_disks()


RAID_ADVICE = ("The BIOS's RAID setting (Intel RST) hides the disk. Restart into the BIOS and set the storage mode "
               "(often called SATA mode or SATA operation) to AHCI. Windows on this disk won't start after that "
               "change, but installing EvenKeelOS erases it anyway.")


def wifi(devices):
    radios = [d for d in devices if kind(d, "0280")]
    ready = [n for n in glob.glob(f"{SYS}/class/net/*") if os.path.isdir(f"{n}/wireless")
             and os.path.basename(os.path.realpath(f"{n}/device/driver")) not in NO_FIRMWARE]
    if ready:
        return (GOOD, "Wi-Fi", "Wi-Fi found.", "")
    todo = "Use a network cable, or a USB Wi-Fi adapter that works with Linux."
    if any(d["vendor"] == BROADCOM for d in radios):
        return (BAD, "Wi-Fi", "Broadcom Wi-Fi chip found. Its driver or firmware can't be included.", todo)
    if any(not d["driver"] for d in radios):
        return (BAD, "Wi-Fi", "A wireless chip was found, with no driver for it.", todo)
    if radios:
        return (BAD, "Wi-Fi", "A wireless chip was found, but it didn't start.",
                todo + " Save the results for your helper.")
    return (LIMITED, "Wi-Fi", "No Wi-Fi found.", "Use a network cable.")


def internal_disks():
    """Sizes in bytes of the disks inside the computer (not USB, not removable)."""
    found = []
    for path in sorted(glob.glob(f"{SYS}/block/*")):
        if not re.match(r"(nvme\d+n\d+|sd[a-z]+|mmcblk\d+|vd[a-z]+)$", os.path.basename(path)):
            continue
        if read(f"{path}/removable") == "1" or "/usb" in os.path.realpath(path):
            continue
        found.append(int(read(f"{path}/size", "0") or 0) * 512)
    return found


def disks(raid):
    found = [size for size in internal_disks() if size >= MIN_DISK]
    if raid:
        if found:
            return (LIMITED, "Disk", f"Disk found, {max(found) / 10 ** 9:.0f} GB. Another disk is hidden by a BIOS "
                    "setting.", RAID_ADVICE)
        return (BAD, "Disk", "The disk is hidden by a BIOS setting.", RAID_ADVICE)
    if not internal_disks():
        return (BAD, "Disk", "No disk inside the computer was found.",
                "Check the BIOS's storage settings. Save the results for your helper.")
    if not found:
        return (BAD, "Disk", f"The biggest disk holds {max(internal_disks()) / 10 ** 9:.0f} GB.",
                "EvenKeelOS needs at least 20 GB.")
    return (GOOD, "Disk", f"Disk found, {max(found) / 10 ** 9:.0f} GB.", "")


def graphics(devices):
    shown = [d for d in devices if kind(d, "03")]
    if "nomodeset" in read(f"{PROC}/cmdline").split():
        return (LIMITED, "Graphics", "Started in basic graphics mode, so graphics can't be checked.",
                "Start the USB stick again with the first entry, EvenKeelOS Live.")
    if not shown:
        return (BAD, "Graphics", "No graphics chip found.", "Save the results for your helper.")
    names = sorted({vendor(d) or "Unknown" for d in shown})
    if "NVIDIA" in names:
        others = [n for n in names if n != "NVIDIA"]
        return (LIMITED, "Graphics", f"{' and '.join(['NVIDIA'] + others)} graphics found.",
                "NVIDIA graphics aren't supported by EvenKeelOS." +
                (f" The {others[0]} graphics are used for the screen." if others else ""))
    if any(not d["driver"] for d in shown):
        return (BAD, "Graphics", "A graphics chip has no driver.", "Save the results for your helper.")
    return (GOOD, "Graphics", f"{' and '.join(names)} graphics found.", "")


def sound(devices):
    cards = read(f"{PROC}/asound/cards")
    if cards and "no soundcards" not in cards:
        return (GOOD, "Sound", "Sound found.", "")
    if any(kind(d, "0401") or kind(d, "0403") for d in devices):
        return (BAD, "Sound", "A sound chip was found, but it didn't start.", "Save the results for your helper.")
    return (LIMITED, "Sound", "No sound found.", "USB or Bluetooth headphones may still work.")


def camera(devices):
    uvc = [v for v in glob.glob(f"{SYS}/class/video4linux/*")
           if os.path.basename(os.path.realpath(f"{v}/device/driver")) == "uvcvideo"]
    if uvc:
        return (GOOD, "Camera", "Camera found.", "")
    ipu = [d for d in devices if d["vendor"] == "0x8086" and kind(d, "0480")
           and (not d["driver"] or "ipu" in d["driver"])]
    if ipu:
        return (LIMITED, "Camera", "A built-in camera of the newer laptop kind was found.",
                "It may not work yet. When it does, it works in Firefox and the Camera app, not every app.")
    return (LIMITED, "Camera", "No camera found.", "A USB webcam works.")


def bluetooth():
    if glob.glob(f"{SYS}/class/bluetooth/hci*"):
        return (GOOD, "Bluetooth", "Bluetooth found.", "")
    return (LIMITED, "Bluetooth", "No Bluetooth found.", "")


def touchpad():
    laptop = bool(glob.glob(f"{SYS}/class/power_supply/BAT*"))
    names = re.findall(r'^N: Name="(.*)"', read(f"{PROC}/bus/input/devices"), re.M)
    if any(t in n.lower() for n in names for t in TOUCHPADS):
        return (GOOD, "Touchpad", "Touchpad found.", "")
    if laptop:
        return (LIMITED, "Touchpad", "No touchpad found.", "A USB mouse works. Save the results for your helper.")
    return None


def start_mode():
    if not os.path.isdir(f"{SYS}/firmware/efi"):
        return (BAD, "Start mode", "This computer started the USB stick in old BIOS (legacy) mode.",
                "EvenKeelOS needs UEFI. Turn on UEFI in the BIOS, then start from the USB stick again.")
    try:
        with open(f"{SYS}/firmware/efi/efivars/SecureBoot-{EFI_GLOBAL}", "rb") as f:
            state = "on" if f.read()[-1:] == b"\x01" else "off"
    except OSError:
        state = "unknown"
    found = {"on": "Secure Boot is on.", "off": "Secure Boot is off.", "unknown": "Started in UEFI mode."}[state]
    return (GOOD, "Secure Boot", found, "Secure Boot on or off is fine.")


def memory():
    kb = re.search(r"^MemTotal:\s+(\d+) kB", read(f"{PROC}/meminfo"), re.M)
    if not kb:
        return None
    gb = int(kb.group(1)) / 1024 ** 2
    shown = f"{math.ceil(gb)} GB of memory."
    if gb < MIN_MEMORY_GB - 1:          # firmware and built-in graphics keep some back
        return (LIMITED, "Memory", shown, "EvenKeelOS works best with 8 GB or more, so it may be slow.")
    return (GOOD, "Memory", shown, "")


def check():
    """Every result, most important first."""
    devices = pci_devices()
    raid = raid_hidden()
    results = [start_mode(), disks(raid), wifi(devices), graphics(devices), sound(devices), memory(),
               camera(devices), bluetooth(), touchpad()]
    return [r for r in results if r]


def report(results):
    """The results as text, for a file."""
    lines = ["EvenKeelOS fit check", ""]
    marks = {GOOD: "OK", LIMITED: "LIMITED", BAD: "PROBLEM"}
    for level, part, found, todo in results:
        lines.append(f"[{marks[level]}] {part}: {found}" + (f" {todo}" if todo else ""))
    lines += ["", "PCI devices (slot, class, vendor, driver):"]
    lines += [f"  {d['slot']} {d['class']} {d['vendor']} {d['driver'] or '(none)'}" for d in pci_devices()]
    return "\n".join(lines) + "\n"
