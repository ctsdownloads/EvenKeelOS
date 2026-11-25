"""What works on this computer, saved after each good start; a new version on trial must keep all of it working.

Each item lists what must still be there for its loss to count, so unplugged or switched-off hardware never counts.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/")                       # the build checks point this at a made-up computer
RECORD = "/var/lib/evenkeel-os/health-record.json"
LOST = "/var/lib/evenkeel-os/health-lost"
DISK_UNLOCK_ON = "/var/lib/evenkeel-os/disk-unlock-on"
BOOT_OPTIONS = "/var/lib/evenkeel-os/boot-options.json"
SHARED_FOLDERS = "/etc/evenkeel-os/shared-folders.json"
SHARES = "/etc/samba/evenkeel-shares.conf"     # the shares Samba is given (folders with a sharing password)
TPM_PCRS = ("7", "14")                          # what automatic disk unlock is tied to (evenkeel-os-tools-admin)
PLACES = ("evenkeel-public", "evenkeel-home", "evenkeel-work")    # evenkeel_os_network's zones (a build check)
# Real services the "A system service fails" test may break (each has the test drop-in); the first one running.
TEST_SERVICES = ("ModemManager.service", "switcheroo-control.service")
FORMAT = 2
VM_DRIVERS = ("vfio-pci", "pci-stub")   # a device given to a virtual machine on purpose (Boot options)
WAIT = 120                              # seconds a trial start waits for slow devices before counting them lost
# While a failed trial asks the person on the screen first; the admin helper's keep-update answers with KEEP.
QUESTION = "/run/evenkeel-os/restart-question"
KEEP = "/run/evenkeel-os/restart-keep"
COUNTDOWN = 120                         # seconds a real problem waits for an answer (evenkeel-os-tools too)
# Crash messages of the system core itself: a kind seen now but not at the last good start counts. An app's own
# fault ("traps: app[pid] general protection fault"), GPU hangs (often one app's) and firmware restarts don't.
CRASHES = {"kernel-bug": re.compile(r"\bBUG: |kernel BUG at "), "oops": re.compile(r"\bOops: "),
           "gpf": re.compile(r"^(?!traps: ).*general protection fault")}
CRASH_NAMES = {"kernel-bug": "The system core reported a bug", "oops": "The system core crashed (an oops)",
               "gpf": "The system core crashed (a protection fault)"}


def P(path):
    return ROOT / str(path).lstrip("/")


def rel(p):
    return "/" + str(Path(p).relative_to(ROOT))


def read(path, default=""):
    try:
        return P(path).read_text().strip()
    except (OSError, UnicodeDecodeError):
        return default


def run(cmd, timeout=30):
    """(exit code, output); 127 when the program is missing or hangs."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=dict(os.environ, LC_ALL="C"))
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""
    return r.returncode, r.stdout


def link_name(p):
    """The name a sysfs link points to (a driver, a module, a bus), or empty."""
    p = Path(p)
    return os.path.basename(os.readlink(p)) if p.is_symlink() else ""


def attr(d, name):
    """A sysfs attribute of a device folder."""
    try:
        return (Path(d) / name).read_text().strip()
    except (OSError, UnicodeDecodeError):
        return ""


def subsystem(d):
    return link_name(Path(d) / "subsystem")


def anchor(dev):
    """The hardware a device hangs off, which stays when its driver fails: PCI or USB, else firmware-made, else bus."""
    try:
        dev = Path(dev).resolve(strict=True)
    except OSError:
        return None
    top = P("/sys/devices")
    if top not in dev.parents:
        return None
    other = firmware = None
    for d in [dev, *dev.parents]:
        if d == top:
            break
        s = subsystem(d)
        if s == "pci" or (s == "usb" and (d / "idVendor").exists()):
            return d
        if s in ("platform", "acpi"):
            firmware = d
        elif other is None and s in ("i2c", "serio", "sdio", "spi"):
            other = d
    return firmware or other


def usb_id(d):
    return f"{attr(d, 'idVendor')}:{attr(d, 'idProduct')}"


def removable(a):
    """A USB device in a port the computer doesn't call fixed: plug-ins, and anything on a hub or dock."""
    return subsystem(a) == "usb" and attr(a, "removable") != "fixed"


def akey(a):
    if subsystem(a) == "usb":
        return "usb:" + usb_id(a)
    return f"{subsystem(a)}:{a.name}"


def need(a):
    """What must still be there for a lost item hanging off this hardware to count."""
    if subsystem(a) == "usb":
        return {"usb": usb_id(a)}
    if subsystem(a) == "pci":
        return {"path": rel(a), "id": f"{attr(a, 'vendor')}:{attr(a, 'device')}"}
    return {"path": rel(a)}


def module(dev):
    """The driver module of a device (empty when it has no driver); without a module link, the driver's own name."""
    drv = Path(dev) / "driver"
    if not drv.exists():
        return ""
    name = link_name(drv / "module") or link_name(drv).replace("-", "_")
    return name if P(f"/sys/module/{name}").exists() else ""


def listed(folder, pattern):
    d = P(folder)
    try:
        return sorted(p for p in d.iterdir() if re.fullmatch(pattern, p.name))
    except OSError:
        return []


def usb_devices():
    """Present USB devices (not their interfaces) and their vendor:product."""
    return {usb_id(d): d for d in listed("/sys/bus/usb/devices", r"[0-9]+-[0-9.]+|usb[0-9]+")}


def hardware(prefix, name, devices):
    """Items for devices that hang off fixed hardware: one per piece of hardware."""
    items = {}
    for dev in devices:
        a = anchor(dev)
        if a is None or removable(a):
            continue
        item = items.setdefault(f"{prefix}:{akey(a)}", {"name": name, "needs": [need(a)], "modules": []})
        if module(dev) not in item["modules"]:
            item["modules"].append(module(dev))
    return items


def sound():
    return hardware("sound", "Sound", [c / "device" for c in listed("/sys/class/sound", r"card[0-9]+")])


def networks():
    wifi, wired = [], []
    for n in listed("/sys/class/net", r".+"):
        if not (n / "device").exists():
            continue
        if (n / "phy80211").exists() or (n / "wireless").exists():
            wifi.append(n / "device")
        elif attr(n, "type") == "1":
            wired.append(n / "device")
    return {**hardware("wifi", "Wi-Fi", wifi), **hardware("wired", "Wired network", wired)}


def bluetooth():
    return hardware("bluetooth", "Bluetooth", [h / "device" for h in listed("/sys/class/bluetooth", r"hci[0-9]+")])


def graphics():
    items = {}
    for c in listed("/sys/class/drm", r"card[0-9]+"):
        drv = module(c / "device") or "its driver"
        items.update(hardware("graphics", f"Graphics ({drv})", [c / "device"]))
    return items


def cameras():
    items = {}
    for v in listed("/sys/class/video4linux", r"video[0-9]+"):
        items.update({k: i for k, i in hardware("camera", f"The camera ({attr(v, 'name') or v.name})",
                                                [v / "device"]).items() if k not in items})
    return items


def inputs():
    items = {}
    for i in listed("/sys/class/input", r"input[0-9]+"):
        rc, props = run(["udevadm", "info", "--query=property", f"--path={rel(i)}"])
        if rc != 0:
            continue
        kind = ("touchpad" if "ID_INPUT_TOUCHPAD=1" in props.split() else
                "keyboard" if "ID_INPUT_KEYBOARD=1" in props.split() else None)
        bus = attr(i, "id/bustype")
        if kind is None or bus in ("0005", "0006"):        # Bluetooth and made-up (virtual) devices come and go
            continue
        a = anchor(i / "device")
        if a is None or removable(a):
            continue
        n = input_need(i / "device") if subsystem(a) != "usb" else need(a)
        if n is None:
            continue
        # A kernel may move a touchpad to a better driver (another bus and name), so any touchpad will do.
        key = "touchpad" if kind == "touchpad" else f"keyboard:{bus}:{attr(i, 'id/vendor')}:{attr(i, 'id/product')}"
        item = items.setdefault(key, {"name": f"The {kind} ({attr(i, 'name') or 'built in'})", "needs": []})
        if n not in item["needs"]:
            item["needs"].append(n)
    return items


def input_need(dev):
    """A built-in keyboard's or touchpad's firmware entry (gone or marked absent when the BIOS switches it off)."""
    try:
        dev = Path(dev).resolve(strict=True)
    except OSError:
        return None
    for d in [dev, *dev.parents]:
        fw = d / "firmware_node"
        if fw.is_symlink():
            return {"path": rel(fw.resolve()), "acpi": True}
        if subsystem(d) in ("i2c", "serio", "spi"):
            return {"path": rel(d)}
    return None


def batteries():
    items = {}
    for b in listed("/sys/class/power_supply", r".+"):
        if attr(b, "type") != "Battery" or attr(b, "scope") == "Device":
            continue
        try:
            a = (b / "device").resolve(strict=True)
        except OSError:
            continue
        a = a if subsystem(a) == "acpi" else anchor(a)
        if a is None:
            continue
        items[f"battery:{akey(a)}"] = {"name": "Battery status", "needs": [dict(need(a), battery=True)]}
    return items


def backlight():
    for b in listed("/sys/class/backlight", r".+"):
        if not b.name.startswith("ddcci") and attr(b, "type") in ("raw", "platform", "firmware"):
            return {"backlight": {"name": "Screen brightness control", "needs": [{"lid": "open"}]}}
    return {}


def thunderbolt():
    return hardware("thunderbolt", "Thunderbolt or USB4 ports",
                    listed("/sys/bus/thunderbolt/devices", r"domain[0-9]+"))


def fprint_ids():
    """USB readers libfprint supports, from the udev hardware lists it ships."""
    ids = set()
    for f in listed("/usr/lib/udev/hwdb.d", r".+\.hwdb"):
        supported = False
        for line in f.read_text(errors="replace").splitlines():
            if line.startswith("#"):
                supported = "libfprint" in line and "unsupported" not in line.lower()
            m = re.match(r"usb:v([0-9A-Fa-f]{4})p([0-9A-Fa-f]{4})", line)
            if m and supported:
                ids.add(f"{m[1].lower()}:{m[2].lower()}")
    return ids


def fingerprint():
    rc, out = run(["busctl", "call", "net.reactivated.Fprint", "/net/reactivated/Fprint/Manager",
                   "net.reactivated.Fprint.Manager", "GetDevices"])
    if rc != 0 or len(out.split()) < 2 or out.split()[1] == "0":
        return {}
    readers = [d for i, d in usb_devices().items() if i in fprint_ids() and not removable(d)]
    return {"fingerprint": {"name": "The fingerprint reader", "needs": [need(d) for d in readers]}} if readers else {}


def enabled(units):
    return {"enabled": list(units)}


def software():
    """Programs and services that must answer: each item is the program working, not the network or settings."""
    items = {}

    def works(key, name, ok, needs=()):
        if ok:
            items[key] = {"name": name, "needs": list(needs)}

    works("printing", "Printing", "scheduler is running" in run(["lpstat", "-r"])[1],
          [enabled(["cups.socket", "cups.service"])])
    works("power-modes", "Power modes",
          run(["busctl", "get-property", "org.freedesktop.UPower.PowerProfiles",
               "/org/freedesktop/UPower/PowerProfiles", "org.freedesktop.UPower.PowerProfiles",
               "ActiveProfile"])[1].startswith("s "),
          [enabled(["tuned-ppd.service", "power-profiles-daemon.service"])])
    works("update-program", "The update program",
          run(["uupd", "--version"])[0] == 0 and run(["rpm-ostree", "status", "--json"], 120)[0] == 0)
    works("flatpak", "The app system (Flatpak)", run(["flatpak", "remotes", "--system", "--columns=name"])[0] == 0)
    works("firmware-updater", "The firmware updater",
          run(["busctl", "get-property", "org.freedesktop.fwupd", "/", "org.freedesktop.fwupd",
               "DaemonVersion"], 60)[1].startswith("s "))
    up = run(["firewall-cmd", "--state"])[0] == 0
    works("firewall", "The firewall", up, [enabled(["firewalld.service"])])
    works("network-places", "Network places (Home, Work, Public place)",
          up and set(PLACES) <= set(run(["firewall-cmd", "--get-zones"])[1].split()), [enabled(["firewalld.service"])])
    works("selinux", "SELinux security", read("/sys/fs/selinux/enforce") == "1")
    works("clock-sync", "Clock sync", run(["systemctl", "is-active", "chronyd.service"])[1].strip() == "active",
          [enabled(["chronyd.service"])])
    works("dns", "Looking up website names (DNS)", run(["resolvectl", "query", "--legend=no", "localhost"])[0] == 0,
          [enabled(["systemd-resolved.service"])])
    cmdline = read("/proc/cmdline").split()
    if P(DISK_UNLOCK_ON).exists() and any(a.startswith("rd.luks.uuid=") for a in cmdline):
        rc, log = run(["journalctl", "-b", "-o", "cat", "--no-pager", "-t", "systemd-cryptsetup"])
        # An unreadable journal says nothing either way, so it counts as working.
        works("disk-unlock", "Automatic disk unlock",
              rc != 0 or not re.search(r"falling back to traditional unlocking|Failed to activate with TPM2", log),
              [{"file": DISK_UNLOCK_ON}, {"pcrs": pcrs()}])
    opts = boot_options()
    works("boot-options", "Your Boot options settings", opts and all(o in cmdline for o in opts),
          [{"config": "boot-options"}])
    # Samba itself runs only on a Home network, so this is its settings: every shared folder in them.
    shares = re.findall(r"^\[(.+)\]$", read(SHARES), re.M)
    if shared_folders() and shares:
        rc, conf = run(["testparm", "-s", "--suppress-prompt"])
        works("shared-folders", "Shared folders", rc == 0 and all(f"[{s}]" in conf for s in shares),
              [{"config": "shared-folders"}])
    return items


def pcrs():
    """The TPM measurements disk unlock depends on; after a firmware change, a failed unlock isn't the version's."""
    return {n: read(f"/sys/class/tpm/tpm0/pcr-sha256/{n}") for n in TPM_PCRS}


def boot_options():
    """The settings Wheelhouse's Boot options added."""
    try:
        opts = json.loads(read(BOOT_OPTIONS, "{}")).get("options", [])
    except (ValueError, AttributeError):
        return []
    return [o for o in opts if isinstance(o, str)] if isinstance(opts, list) else []


def shared_folders():
    """Share names, when Shared folders is on."""
    try:
        s = json.loads(read(SHARED_FOLDERS, "{}"))
    except ValueError:
        return []
    if not isinstance(s, dict) or s.get("on") is not True:
        return []
    return [f["name"] for f in s.get("folders", []) if isinstance(f, dict) and isinstance(f.get("name"), str)]


def drivers():
    """Every PCI device, and every USB device in a fixed port, that has a driver."""
    items = {}
    for d in listed("/sys/bus/pci/devices", r".+"):
        drv = link_name(d / "driver")
        if drv and drv not in VM_DRIVERS:
            items[f"driver:pci:{d.name}"] = {"name": f"A device lost its driver ({drv})", "needs": [need(d.resolve())]}
    for d in listed("/sys/bus/usb/devices", r"[0-9]+-[0-9.]+:[0-9]+\.[0-9]+"):
        drv = link_name(d / "driver")
        dev = d.resolve().parent
        if drv in ("", "usbfs") or removable(dev):        # usbfs: claimed by a program while it runs
            continue
        items[f"driver:usb:{usb_id(dev)}:{d.name.split(':')[1]}"] = {
            "name": f"A device lost its driver ({drv})", "needs": [need(dev)]}
    return items


def services():
    """Services running now (long-running ones: a one-time job may fail offline, which never counts)."""
    _, out = run(["systemctl", "list-units", "--type=service", "--state=running", "--plain", "--no-legend",
                  "--no-pager"])
    items = {}
    for line in out.splitlines():
        f = line.lstrip("\u25cf* ").split(None, 4)      # a failed unit can start with a dot
        if len(f) >= 4 and f[0].endswith(".service"):
            desc = f[4] if len(f) > 4 else f[0]
            name = desc if desc.lower().endswith("service") else f"{desc} service"
            items[f"service:{f[0]}"] = {"name": f"The {name} ({f[0]})", "needs": []}
    return items


def failed_services():
    _, out = run(["systemctl", "list-units", "--type=service", "--state=failed", "--plain", "--no-legend",
                  "--no-pager"])
    return {w for line in out.splitlines() for w in line.split()[:2] if w.endswith(".service")}


def crashes():
    _, out = run(["journalctl", "-k", "-b", "-o", "cat", "--no-pager"], 60)
    found = {}
    for line in out.splitlines():
        for kind, pattern in CRASHES.items():
            if kind not in found and pattern.search(line):
                found[kind] = line.strip()[:160]
    return found


def machine():
    """Which computer this is, so a disk moved to another computer isn't compared with the old one."""
    return read("/sys/class/dmi/id/product_uuid") or (read("/sys/class/dmi/id/board_vendor") + ":" +
                                                      read("/sys/class/dmi/id/product_name"))


PROBES = (sound, networks, bluetooth, graphics, cameras, inputs, batteries, backlight, thunderbolt, fingerprint,
          software, drivers, services)


def gather():
    items = {}
    for probe in PROBES:
        items.update(probe())
    return items


def holds(n):
    """Whether what a lost item needs is still there."""
    if "usb" in n:
        dev = usb_devices().get(n["usb"])
        return dev is not None and not removable(dev)
    if "enabled" in n:
        return any(run(["systemctl", "is-enabled", u])[1].strip() in ("enabled", "static") for u in n["enabled"])
    if "file" in n:
        return P(n["file"]).exists()
    if "lid" in n:                         # a closed lid can leave the screen's brightness control out
        return not any("closed" in attr(d, "state") for d in listed("/proc/acpi/button/lid", r".+"))
    if "pcrs" in n:
        return n["pcrs"] == pcrs()
    if "config" in n:
        return bool(boot_options() if n["config"] == "boot-options" else shared_folders())
    d = P(n["path"])
    if not d.exists() or link_name(d / "driver") in VM_DRIVERS:     # a device given to a virtual machine
        return False
    if "id" in n and f"{attr(d, 'vendor')}:{attr(d, 'device')}" != n["id"]:
        return False
    if not (n.get("battery") or n.get("acpi")):
        return True
    status = attr(d, "status")
    present = 0x10 if n.get("battery") else 0x01           # ACPI's "battery present" and "device present" bits
    return not status.isdigit() or bool(int(status) & present)


# What a start that only changed boot options (Wheelhouse, Boot options) still checks: those may switch hardware or
# SELinux off on purpose (nomodeset, module_blacklist=, selinux=0), so hardware items are left to that choice.
SOFTWARE_KEYS = {"service", "printing", "power-modes", "update-program", "flatpak", "firmware-updater", "firewall",
                 "network-places", "clock-sync", "dns", "boot-options", "shared-folders"}


def own_kargs():
    """This start's boot options, without the boot menu's own entries."""
    return sorted(a for a in read("/proc/cmdline").split()
                  if a.split("=", 1)[0] not in ("BOOT_IMAGE", "initrd", "ostree"))


def options_only(record=None):
    """Whether this start's boot options differ from the last good start's (Wheelhouse, Boot options, also with an
    update waiting), or it's the previous version with other boot options; never for a rollback test copy."""
    if "evenkeel_os.test_rollback=" in read("/proc/cmdline"):
        return False
    if record and isinstance(record.get("kargs"), list) and record["kargs"] != own_kargs():
        return True
    rc, out = run(["rpm-ostree", "status", "--json"], 120)
    try:
        ds = json.loads(out)["deployments"]
        booted = next(d["checksum"] for d in ds if d.get("booted"))
        other = next(d["checksum"] for d in ds if not d.get("booted"))
    except (ValueError, KeyError, TypeError, StopIteration):
        return False
    return booted == other


def lost(record):
    """What worked at the record's start and is broken now: [(key, plain words)]."""
    now = gather()
    failed = failed_services()
    hardware_too = not options_only(record)
    out = []
    for key, item in record.get("items", {}).items():
        if not hardware_too and key.split(":", 1)[0] not in SOFTWARE_KEYS:
            continue
        if key.startswith("service:"):
            if key.split(":", 1)[1] in failed:
                out.append((key, item["name"]))
        elif key not in now and all(holds(n) for n in item.get("needs", [])):
            out.append((key, item["name"]))
    for kind, line in crashes().items():
        if kind not in record.get("crashes", {}):
            out.append((f"crash:{kind}", f"{CRASH_NAMES[kind]}: {line}"))
    return out


# Rollback tests that need something this computer has: the record items they break.
DRIVER_TESTS = {"sound": (sound, "sound:"), "wifi": (networks, "wifi:"), "bluetooth": (bluetooth, "bluetooth:"),
                "graphics": (graphics, "graphics:")}
SOFTWARE_TESTS = {"printing": "printing", "firewall": "firewall", "update-program": "update-program"}
TRIAL_TESTS = (*DRIVER_TESTS, *SOFTWARE_TESTS, "service")    # the tests this check fails


def loadable(mod):
    """Whether a driver module was loaded from a file (a driver built into the system can't be blocked)."""
    return bool(mod) and P(f"/sys/module/{mod}/initstate").exists()


def test_args(kind):
    """The extra kernel arguments a rollback test needs here, or an exit code: 7 no list of what works saved yet,
    8 this computer doesn't have the thing the test breaks, 9 none of its drivers can be blocked (built in)."""
    if kind not in DRIVER_TESTS and kind not in SOFTWARE_TESTS and kind != "service":
        return []
    rec = load()
    if rec is None or rec.get("machine") != machine():
        return 7
    if kind in DRIVER_TESTS:
        probe, prefix = DRIVER_TESTS[kind]
        now = probe()
        working = [i for k, i in now.items() if k.startswith(prefix) and k in rec["items"]]
        if not working:
            return 8
        # Devices whose drivers can all be blocked (a built-in one, like a basic startup screen, stays working).
        mods = {m for i in working if all(loadable(m) for m in i["modules"]) for m in i["modules"]}
        if not mods:
            return 9
        # One module_blacklist= counts (the last), so the owner's own blocks stay in it.
        own = [m for a in read("/proc/cmdline").split() if a.startswith("module_blacklist=")
               for m in a.split("=", 1)[1].split(",") if m]
        return [f"module_blacklist={','.join(dict.fromkeys(own + sorted(mods)))}"]
    if kind in SOFTWARE_TESTS:
        return [] if SOFTWARE_TESTS[kind] in rec["items"] else 8
    if kind == "service":
        return [] if any(f"service:{u}" in rec["items"] for u in TEST_SERVICES) else 8
    return []


def load(path=RECORD):
    try:
        r = json.loads(P(path).read_text())
    except (OSError, ValueError):
        return None
    return r if isinstance(r, dict) and r.get("format") == FORMAT and isinstance(r.get("items"), dict) else None


def write(path, text):
    p = P(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(text)
    tmp.chmod(0o644)
    os.replace(tmp, p)


def record(settle=240):
    """Save what works now, once the computer has been up long enough for slow devices (settle seconds)."""
    try:
        up = float(read("/proc/uptime", "0").split()[0])
    except (ValueError, IndexError):
        up = 0
    if up < settle:
        time.sleep(settle - up)
    rec = {"format": FORMAT, "machine": machine(), "time": int(time.time()), "items": gather(), "crashes": crashes(),
           "kargs": own_kargs()}
    write(RECORD, json.dumps(rec, indent=1, sort_keys=True) + "\n")
    return len(rec["items"])


def compare(wait=None, path=RECORD, note=False):
    """Exit code 1 when something that worked at the last good start is broken now (after waiting for it)."""
    rec = load(path)
    if rec is None:
        print("No list of what works has been saved yet, so there's nothing to compare.")
        return 0
    if rec.get("machine") != machine():
        print("The saved list is from another computer, so there's nothing to compare.")
        return 0
    end = time.monotonic() + (WAIT if wait is None else wait)
    try:
        while True:
            gone = lost(rec)
            if not gone or time.monotonic() >= end:
                break
            time.sleep(5)
    except Exception as e:     # noqa: BLE001  a mistake here must never roll a good version back
        print(f"The comparison itself failed ({e!r}), so it doesn't count against this start.")
        return 0
    if not gone:
        P(LOST).unlink(missing_ok=True)
        print(f"Everything that worked at the last good start ({len(rec['items'])} things) still works.")
        return 0
    for key, name in gone:
        print(f"Stopped working: {name} [{key}]")
    if note:                               # the trial's list, for the rollback note
        write(LOST, f"{int(time.time())}\n" + "".join(f"{name}\n" for _, name in gone))
    return 1


USAGE = "Usage: evenkeel-os-health trial | record [--now] | compare [--no-wait] [--record=FILE]"


def on_trial():
    """A new version greenboot is trying (named in the boot menu's settings), not a fallback to the previous one."""
    env = run(["grub2-editenv", "/boot/grub2/grubenv", "list"])[1].split()
    return any(v.startswith("greenboot_next_deployment_id=") for v in env) and "boot_counter=-1" not in env


def last_start():
    """Whether greenboot goes back after this failure (its retries are used up) instead of trying again."""
    for v in run(["grub2-editenv", "/boot/grub2/grubenv", "list"])[1].split():
        if v.startswith("boot_counter="):
            try:
                return int(v.split("=", 1)[1]) <= 0
            except ValueError:
                return False
    return False


def trial_kind():
    """The test this start runs, "boot-options" for the same system with other boot options, or "update"."""
    for a in read("/proc/cmdline").split():
        if a.startswith("evenkeel_os.test_rollback="):
            return a.split("=", 1)[1]
    # As 90-evenkeel-os-rolled-back.sh tells them apart: the running version and the other one on disk.
    try:
        ds = json.loads(run(["rpm-ostree", "status", "--json"], 60)[1])["deployments"]
        sums = [d["checksum"] for d in ds if d.get("booted")] + [d["checksum"] for d in ds if not d.get("booted")][:1]
    except (ValueError, KeyError, TypeError):
        return "update"
    return "boot-options" if len(sums) == 2 and sums[0] == sums[1] else "update"


def desktop_user():
    """(name, user ID, Wayland display) of the person on the screen now, or None."""
    rc, sid = run(["loginctl", "show-seat", "seat0", "--property=ActiveSession", "--value"])
    if rc != 0 or not sid.strip():
        return None
    rc, out = run(["loginctl", "show-session", sid.strip(), "--property=Name", "--property=User", "--property=Type",
                   "--property=Class", "--property=State"])
    p = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    if rc != 0 or (p.get("Class"), p.get("Type"), p.get("State")) != ("user", "wayland", "active"):
        return None
    if not p.get("Name") or not p.get("User", "").isdigit():
        return None
    sockets = sorted(s.name for s in P(f"/run/user/{p['User']}").glob("wayland-*") if not s.name.endswith(".lock"))
    return (p["Name"], p["User"], sockets[0]) if sockets else None


def question(cmd, name, cap):
    """Runs the window and waits for it: its exit code (0 restart now, 3 keep), or 1 when it can't start, the person
    logs out or it runs past cap seconds (None: no limit)."""
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return 1
    end = None if cap is None else time.monotonic() + cap
    while p.poll() is None:
        time.sleep(5)
        if p.poll() is None and (desktop_user() is None or (end and time.monotonic() > end)):
            p.kill()
            p.wait()
            run(["systemctl", f"--machine={name}@.host", "--user", "stop", "evenkeel-os-restart-question.service"])
            return 1
    return p.returncode


def ask_first():
    """Before greenboot restarts a failed trial, the person on the screen answers; 0 keeps this version running."""
    try:
        who = desktop_user()
        if who is None:
            print("Nobody is on the screen to ask, so it restarts now.")
            return 1
        name, _, display = who
        kind = trial_kind()
        start = "last" if last_start() else "first"
        bid = read("/proc/sys/kernel/random/boot_id").strip()
        P(KEEP).unlink(missing_ok=True)
        # The boot ID, then what broke, for the window (evenkeel-os-tools reads it) and the admin helper.
        write(QUESTION, "".join(f"{line}\n" for line in [bid, *read(LOST).splitlines()[1:]]))
        # In the person's own session, so the password window works; a time limit backs up a real problem's countdown.
        cmd = ["systemd-run", f"--machine={name}@.host", "--user", "--wait", "--quiet", "--collect",
               "--unit=evenkeel-os-restart-question", f"--setenv=WAYLAND_DISPLAY={display}"]
        if kind not in TRIAL_TESTS:
            cmd.append(f"--property=RuntimeMaxSec={COUNTDOWN + 120}")
        cmd += ["/usr/bin/evenkeel-os-tools", "restart-question", kind, start]
        print(f"Asking {name} on the screen before restarting ({kind}, {start} bad start).")
        rc = question(cmd, name, None if kind in TRIAL_TESTS else COUNTDOWN + 180)
        k = P(KEEP)
        kept = rc == 3 and k.is_file() and k.stat().st_uid == 0 and k.read_text().strip() == bid
    except Exception as e:     # noqa: BLE001  a mistake here must never stop a restart
        print(f"Asking first failed ({e!r}), so it restarts now.")
        return 1
    finally:
        P(QUESTION).unlink(missing_ok=True)
        P(KEEP).unlink(missing_ok=True)
    if kept:
        P(LOST).unlink(missing_ok=True)
        print("Keep was picked, with the administrator password, so this start passes.")
        return 0
    print("Restart now was picked, or no answer came, so it restarts now.")
    return 1


def main(argv):
    if argv[1:] == ["trial"]:
        if not on_trial():
            print("This start isn't a new version on trial, so there's nothing to compare.")
            return 0
        return compare(note=True) and ask_first()
    if argv[1:] in (["record"], ["record", "--now"]):
        print(f"Saved {record(0 if '--now' in argv else 240)} things that work.")
    elif argv[1:2] == ["compare"] and len(argv) <= 4:
        args = argv[2:]
        wait = 0 if "--no-wait" in args else None
        path = next((a.split("=", 1)[1] for a in args if a.startswith("--record=")), RECORD)
        if any(a != "--no-wait" and not a.startswith("--record=") for a in args):
            print(USAGE)
            return 2
        return compare(wait, path)
    else:
        print(USAGE)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
