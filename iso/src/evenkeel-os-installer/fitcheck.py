"""The fit check on the live USB: whether this computer's parts will work with EvenKeelOS, read from the kernel."""
import glob
import math
import os
import re
import sys

from i18n import _, N_

sys.path.insert(0, "/usr/lib/evenkeel-os")
from evenkeel_os_ui import answer  # noqa: E402

SYS = "/sys"
PROC = "/proc"
GOOD, LIMITED, BAD = "good", "limited", "bad"
VENDORS = {"0x8086": "Intel", "0x1002": "AMD", "0x10de": "NVIDIA", "0x14e4": "Broadcom", "0x10ec": "Realtek",
           "0x14c3": "MediaTek", "0x168c": "Qualcomm Atheros", "0x17cb": "Qualcomm"}
BROADCOM = "0x14e4"
NVIDIA = N_("The NVIDIA card runs on the open-source driver built into EvenKeelOS. The proprietary NVIDIA driver "
            "isn't used: it breaks too often to keep the promise that EvenKeelOS just works. If you need it, use "
            "Bazzite or Bluefin's NVIDIA editions instead.")
NO_FIRMWARE = ("b43", "b43legacy")           # Broadcom drivers whose firmware Fedora can't include
RAID_HIDDEN = re.compile(r"remapped NVMe devices|Switch your BIOS from RAID to AHCI")
EFI_GLOBAL = "8be4df61-93ca-11d2-aa0d-00e098032b8c"
MIN_DISK = 20 * 10 ** 9                      # Fedora Workstation's minimum disk
MIN_MEMORY_GB = 8                            # the README's recommended amount
TOUCHPADS = ("touchpad", "trackpad", "glidepoint", "synaptics", "bcm5974")


class Text(str):
    """What the person reads, with the English it was made from (the saved results file stays English)."""
    english = ""


def words(template, **values):
    """The template in the installer's language with its values put in."""
    text = Text(_(template).format(**values))
    text.english = template.format(**{k: getattr(v, "english", "") or v for k, v in values.items()})
    return text


def joined(*parts):
    """Whole sentences one after the other."""
    text = Text(" ".join(parts))
    text.english = " ".join(getattr(p, "english", p) for p in parts)
    return text


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
        r = answer(cmd)
        if r and r.returncode == 0 and r.stdout.strip():
            return r.stdout
    return ""


def raid_hidden(log=None):
    """Whether the BIOS's RAID (Intel RST) setting hides a disk from Linux."""
    if log is not None:
        return bool(RAID_HIDDEN.search(log))
    log = kernel_log()
    if log:
        return bool(RAID_HIDDEN.search(log))
    rst = any(d["vendor"] == "0x8086" and kind(d, "0104") and d["driver"] == "ahci" for d in pci_devices())
    return rst and not internal_disks()


RAID_ADVICE = N_("The BIOS's RAID setting (Intel RST) hides the disk. Restart into the BIOS and set the storage mode "
                 "(often called SATA mode or SATA operation) to AHCI. Windows on this disk won't start after that "
                 "change, but installing EvenKeelOS erases it anyway.")


def save_results():
    return words(N_("Save the results for your helper."))


def wifi(devices):
    radios = [d for d in devices if kind(d, "0280")]
    ready = [n for n in glob.glob(f"{SYS}/class/net/*") if os.path.isdir(f"{n}/wireless")
             and os.path.basename(os.path.realpath(f"{n}/device/driver")) not in NO_FIRMWARE]
    part = words(N_("Wi-Fi"))
    if ready:
        return (GOOD, part, words(N_("Wi-Fi found.")), "")
    todo = words(N_("Use a network cable, or a USB Wi-Fi adapter that works with Linux."))
    if any(d["vendor"] == BROADCOM for d in radios):
        return (BAD, part, words(N_("Broadcom Wi-Fi chip found. Its driver or firmware can't be included.")), todo)
    if any(not d["driver"] for d in radios):
        return (BAD, part, words(N_("A wireless chip was found, with no driver for it.")), todo)
    if radios:
        return (BAD, part, words(N_("A wireless chip was found, but it didn't start.")),
                joined(todo, save_results()))
    return (LIMITED, part, words(N_("No Wi-Fi found.")), words(N_("Use a network cable.")))


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
    part = words(N_("Disk"))
    if raid:
        if found:
            return (LIMITED, part, joined(words(N_("Disk found, {gb} GB."), gb=f"{max(found) / 10 ** 9:.0f}"),
                                          words(N_("Another disk is hidden by a BIOS setting."))),
                    words(RAID_ADVICE))
        return (BAD, part, words(N_("The disk is hidden by a BIOS setting.")), words(RAID_ADVICE))
    if not internal_disks():
        return (BAD, part, words(N_("No disk inside the computer was found.")),
                joined(words(N_("Check the BIOS's storage settings.")), save_results()))
    if not found:
        return (BAD, part, words(N_("The biggest disk holds {gb} GB."), gb=f"{max(internal_disks()) / 10 ** 9:.0f}"),
                words(N_("EvenKeelOS needs at least 20 GB.")))
    return (GOOD, part, words(N_("Disk found, {gb} GB."), gb=f"{max(found) / 10 ** 9:.0f}"), "")


def graphics_found(names):
    if len(names) == 1:
        return words(N_("{names} graphics found."), names=names[0])
    return words(N_("{names} and {last} graphics found."), names=", ".join(names[:-1]), last=names[-1])


def graphics(devices):
    shown = [d for d in devices if kind(d, "03")]
    part = words(N_("Graphics"))
    if "nomodeset" in read(f"{PROC}/cmdline").split():
        return (LIMITED, part, words(N_("Started in basic graphics mode, so graphics can't be checked.")),
                words(N_("Start the USB stick again with the first entry, EvenKeelOS Live.")))
    if not shown:
        return (BAD, part, words(N_("No graphics chip found.")), save_results())
    names = sorted({vendor(d) or words(N_("Unknown")) for d in shown})
    if any(not d["driver"] for d in shown):
        return (BAD, part, words(N_("A graphics chip has no driver.")), save_results())
    if "NVIDIA" in names:
        others = [n for n in names if n != "NVIDIA"]
        found = graphics_found(["NVIDIA"] + others)
        if others:
            return (GOOD, part, found, joined(words(N_("The {name} graphics drive the screen."), name=others[0]),
                                              words(NVIDIA)))
        return (GOOD, part, found, words(NVIDIA))
    return (GOOD, part, graphics_found(names), "")


def sound(devices):
    cards = read(f"{PROC}/asound/cards")
    if cards and "no soundcards" not in cards:
        return (GOOD, words(N_("Sound")), words(N_("Sound found.")), "")
    if any(kind(d, "0401") or kind(d, "0403") for d in devices):
        return (BAD, words(N_("Sound")), words(N_("A sound chip was found, but it didn't start.")), save_results())
    return (LIMITED, words(N_("Sound")), words(N_("No sound found.")),
            words(N_("USB or Bluetooth headphones may still work.")))


def camera(devices):
    uvc = [v for v in glob.glob(f"{SYS}/class/video4linux/*")
           if os.path.basename(os.path.realpath(f"{v}/device/driver")) == "uvcvideo"]
    if uvc:
        return (GOOD, words(N_("Camera")), words(N_("Camera found.")), "")
    ipu = [d for d in devices if d["vendor"] == "0x8086" and kind(d, "0480")
           and (not d["driver"] or "ipu" in d["driver"])]
    if ipu:
        return (LIMITED, words(N_("Camera")), words(N_("A built-in camera of the newer laptop kind was found.")),
                words(N_("It may not work yet. When it does, it works in Firefox and the Camera app, not every app.")))
    return (LIMITED, words(N_("Camera")), words(N_("No camera found.")), words(N_("A USB webcam works.")))


def bluetooth():
    if glob.glob(f"{SYS}/class/bluetooth/hci*"):
        return (GOOD, words(N_("Bluetooth")), words(N_("Bluetooth found.")), "")
    return (LIMITED, words(N_("Bluetooth")), words(N_("No Bluetooth found.")), "")


def touchpad():
    laptop = bool(glob.glob(f"{SYS}/class/power_supply/BAT*"))
    names = re.findall(r'^N: Name="(.*)"', read(f"{PROC}/bus/input/devices"), re.M)
    if any(t in n.lower() for n in names for t in TOUCHPADS):
        return (GOOD, words(N_("Touchpad")), words(N_("Touchpad found.")), "")
    if laptop:
        return (LIMITED, words(N_("Touchpad")), words(N_("No touchpad found.")),
                joined(words(N_("A USB mouse works.")), save_results()))
    return None


def start_mode():
    if not os.path.isdir(f"{SYS}/firmware/efi"):
        return (BAD, words(N_("Start mode")),
                words(N_("This computer started the USB stick in old BIOS (legacy) mode.")),
                words(N_("EvenKeelOS needs UEFI. Turn on UEFI in the BIOS, then start from the USB stick again.")))
    try:
        with open(f"{SYS}/firmware/efi/efivars/SecureBoot-{EFI_GLOBAL}", "rb") as f:
            state = "on" if f.read()[-1:] == b"\x01" else "off"
    except OSError:
        state = "unknown"
    found = {"on": N_("Secure Boot is on."), "off": N_("Secure Boot is off."),
             "unknown": N_("Started in UEFI mode.")}[state]
    return (GOOD, words(N_("Secure Boot")), words(found), words(N_("Secure Boot on or off is fine.")))


def memory():
    kb = re.search(r"^MemTotal:\s+(\d+) kB", read(f"{PROC}/meminfo"), re.M)
    if not kb:
        return None
    gb = int(kb.group(1)) / 1024 ** 2
    shown = words(N_("{gb} GB of memory."), gb=math.ceil(gb))
    if gb < MIN_MEMORY_GB - 1:          # firmware and built-in graphics keep some back
        return (LIMITED, words(N_("Memory")), shown,
                words(N_("EvenKeelOS works best with 8 GB or more, so it may be slow.")))
    return (GOOD, words(N_("Memory")), shown, "")


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
        part, found, todo = (getattr(x, "english", x) for x in (part, found, todo))
        lines.append(f"[{marks[level]}] {part}: {found}" + (f" {todo}" if todo else ""))
    lines += ["", "PCI devices (slot, class, vendor, driver):"]
    lines += [f"  {d['slot']} {d['class']} {d['vendor']} {d['driver'] or '(none)'}" for d in pci_devices()]
    return "\n".join(lines) + "\n"
