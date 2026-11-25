"""Boot options: kernel settings the computer starts with, changed in Wheelhouse.

rpm-ostree changes them on the version that starts next (a waiting update keeps them), and every update after
carries them forward. Each change makes a new version, so the one before stays as the fallback.
"""
import json
import re
import subprocess
from pathlib import Path

# The settings Wheelhouse added, so it can take them out; in /var, the same for every version.
STATE = Path("/var/lib/evenkeel-os/boot-options.json")
MAX = 20
SETTING = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}(=[A-Za-z0-9_.,:/+=@!-]{1,128})?$")

# (settings, title, what it fixes). Settings with the same name before "=" replace each other.
COMMON = [
    (("amdgpu.sg_display=0",), "AMD: white flickering", "The screen flashes white, often with an outside display"),
    (("amdgpu.dcdebugmask=0x10",), "AMD: flicker, turn off Panel Self Refresh",
     "Flicker or glitches when the picture is still. The usual fix to try first"),
    (("amdgpu.dcdebugmask=0x400",), "AMD: flicker, turn off Panel Replay", "Glitches on newer AMD chips"),
    (("amdgpu.dcdebugmask=0x410",), "AMD: flicker, turn off both", "When neither of the two above is enough"),
    (("amdgpu.abmlevel=0",), "AMD: screen dims or shifts colors on its own", "Turns off adaptive backlight"),
    (("i915.enable_psr=0",), "Intel (older chips): flicker or freezes", "Turns off Panel Self Refresh"),
    (("xe.enable_psr=0", "xe.enable_panel_replay=0"), "Intel (newest chips): flicker or black flashes",
     "Turns off Panel Self Refresh and Panel Replay"),
    (("nvme_core.default_ps_max_latency_us=0",), "Drive freezes or disappears",
     "Keeps the drive out of its deepest power saving"),
]
COMMON_SETTINGS = {s for settings, _, _ in COMMON for s in settings}

SECURITY = "It turns off or weakens a security protection."
NO_DESKTOP = "The computer would start without the desktop: a text screen or a rescue shell."
NO_PICTURE = "It turns off the graphics driver: low resolution, no outside screens, and sleep may not work."
NO_START = "The computer may not start, or may lose its drive, memory or processors."
SHELL = "It gives anyone at the keyboard a shell with full control, with no password."
OFF = {"0", "n", "no", "off", "f", "false"}
# Name (with - read as _, as the kernel does) -> why it's risky: asked about first, added only if confirmed.
ALWAYS_RISKY = {
    "security": SECURITY, "lsm": SECURITY, "lockdown": SECURITY, "nopti": SECURITY, "nokaslr": SECURITY,
    "nospectre_v1": SECURITY, "nospectre_v2": SECURITY, "sysrq_always_enabled": SECURITY,
    "nospec_store_bypass_disable": SECURITY, "nosmap": SECURITY, "nosmep": SECURITY,
    "rd.break": NO_DESKTOP, "single": NO_DESKTOP, "emergency": NO_DESKTOP, "rescue": NO_DESKTOP,
    "rd.rescue": NO_DESKTOP, "rd.emergency": NO_DESKTOP, "s": NO_DESKTOP, "1": NO_DESKTOP, "2": NO_DESKTOP,
    "3": NO_DESKTOP, "4": NO_DESKTOP, "systemd.mask": NO_DESKTOP, "rd.systemd.mask": NO_DESKTOP,
    "nomodeset": NO_PICTURE,
    "noapic": NO_START, "nolapic": NO_START, "nosmp": NO_START, "noefi": NO_START, "mem": NO_START,
    "memmap": NO_START, "maxcpus": NO_START, "nr_cpus": NO_START,
}
# Name -> (values that are risky, why). Other values are fine: selinux=1 only makes it stricter.
RISKY_WHEN = {
    "selinux": ({"0"}, "It turns off SELinux, which keeps apps and services from reaching what they shouldn't."),
    "enforcing": ({"0"}, "SELinux would stop blocking anything."),
    "module.sig_enforce": ({"0", "n", "off", "no"}, "Unsigned kernel drivers could load."),
    "mitigations": ({"off"}, "It turns off protection against processor security flaws."),
    "pti": ({"off"}, SECURITY), "spectre_v2": ({"off"}, SECURITY), "iommu": ({"off"}, SECURITY),
    "intel_iommu": ({"off"}, SECURITY), "amd_iommu": ({"off"}, SECURITY), "audit": ({"0"}, SECURITY),
    "spectre_v2_user": ({"off"}, SECURITY), "spec_store_bypass_disable": ({"off"}, SECURITY),
    "l1tf": ({"off"}, SECURITY), "mds": ({"off"}, SECURITY), "retbleed": ({"off"}, SECURITY),
    "tsx": ({"on"}, SECURITY), "kvm.nx_huge_pages": ({"off"}, SECURITY),
    "acpi": ({"off", "noirq"}, NO_START), "efi": ({"noruntime"}, NO_START), "amdgpu.dc": ({"0"}, NO_PICTURE),
}
# Shells: risky with any value but a clear "off" (systemd also takes a screen name, like tty9).
SHELLS = ("rd.shell", "systemd.debug_shell", "rd.systemd.debug_shell")
# Set by the system itself; changing them stops it starting, so they can't be added here.
SYSTEM = {"root", "rootflags", "rootfstype", "ostree", "rw", "ro", "boot_image", "initrd", "fstab", "rd.fstab",
          "rd.auto", "systemd.volatile", "luks"}
SYSTEM_PREFIXES = ("rd.luks", "luks.", "rd.lvm", "rd.md", "rd.dm", "ostree.", "composefs", "mount.usr")
# Run a program with full control while starting: refused, since anything that changed the file would run as root.
RUNS_PROGRAM = ("init", "rdinit", "systemd.run")


def name(setting):
    """The part before "=", read the way the kernel and systemd read it (- and _ are the same)."""
    return setting.split("=", 1)[0].replace("-", "_").lower()


def number(value):
    """A number written any way the kernel takes it (00, 0x0) as plain digits; anything else in lowercase."""
    try:
        return str(int(value, 0))
    except ValueError:
        return value.lower()


def problem(setting):
    """Why a setting can't be added ("" when it can)."""
    if '"' in setting or "'" in setting:
        return "Settings with quotes or spaces in their value can't be added here."
    if not SETTING.match(setting):
        return f"{setting!r} isn't a kernel setting. Use letters, numbers and . _ - like amdgpu.abmlevel=0."
    key = name(setting)
    if key.startswith("evenkeel_os."):
        return f"{key} is for Wheelhouse's own tests (Test automatic rollback)."
    if key in SYSTEM or key.startswith(SYSTEM_PREFIXES):
        return f"{key} is set by the system itself. Changing it would stop the computer starting."
    if key in RUNS_PROGRAM or key.startswith("systemd.run"):
        return f"{key} runs a program with full control while the computer starts, so it can't be added here."
    return ""


def risk(setting):
    """Why a setting is risky ("" when it isn't)."""
    key, value = name(setting), number(setting.partition("=")[2])
    if key in ALWAYS_RISKY:
        return ALWAYS_RISKY[key]
    if key in SHELLS:
        return "" if value in OFF else SHELL
    if key in RISKY_WHEN:
        values, why = RISKY_WHEN[key]
        return why if value in values else ""
    if key in ("systemd.unit", "rd.systemd.unit") and value != "graphical.target":
        return NO_DESKTOP
    if "blacklist" in key:
        return "It stops a driver from loading. If it's the drive's or the screen's driver, the computer won't start."
    if key.endswith(".modeset") and value == "0":
        return NO_PICTURE
    return ""


def merged(current, adding):
    """current with adding put in: a setting with the same name replaces the old one, and none is doubled."""
    out = [s for s in current if name(s) not in {name(a) for a in adding}]
    for s in adding:
        if name(s) not in {name(x) for x in out}:
            out.append(s)
    return out


def added():
    """The settings Wheelhouse added (and may take out)."""
    try:
        options = json.loads(STATE.read_text()).get("options", [])
    except (OSError, ValueError, AttributeError):
        return []
    return [s for s in options if isinstance(s, str) and not problem(s)]


def next_start():
    """The settings the next start uses (a waiting version's, or this one's), or None when they can't be read.
    rpm-ostree tells anyone this, with no password."""
    try:
        r = subprocess.run(["/usr/bin/rpm-ostree", "kargs"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.split() if r.returncode == 0 else None


def running():
    """The settings this start used."""
    try:
        return Path("/proc/cmdline").read_text().split()
    except OSError:
        return []


def same(next_settings, running_settings):
    """Whether the next start uses the settings this one did (the boot menu's own entries aside)."""
    def own(settings):
        return sorted(s for s in settings if name(s) not in ("boot_image", "initrd", "ostree"))
    return own(next_settings) == own(running_settings)
