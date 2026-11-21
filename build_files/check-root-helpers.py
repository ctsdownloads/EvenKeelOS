#!/usr/bin/python3 -I
"""Build check: the root helpers refuse hostile input, and no-password permissions stay at the computer only.

Runs in the image build, as root, against the installed helpers. Nothing here changes the system: helper calls
use input each helper must refuse before doing anything, and rule files go to a scratch folder.
"""
import importlib.machinery
import importlib.util
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

LIBEXEC = Path("/usr/libexec")
RULES_D = Path("/usr/share/polkit-1/rules.d")
ACTIONS = Path("/usr/share/polkit-1/actions")
problems = []
# A helper that hangs (on a pipe, say) fails the build instead of stalling it.
signal.signal(signal.SIGALRM, lambda *_: sys.exit("ERROR: a root helper hung on hostile input"))
signal.alarm(300)


def bad(msg):
    problems.append(msg)


def refuses(helper, args, codes=(2,)):
    """The helper exits with a refusal code before doing anything."""
    r = subprocess.run([str(LIBEXEC / helper), *args], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                       timeout=60)
    if r.returncode not in codes:
        bad(f"{helper} {args!r} exited {r.returncode}, not {codes}: it didn't refuse")


HOSTILE = ["", "x", "--help", "-rf /", "a b", "../../etc/shadow", "$(id)", "`id`", "; id", "| id", "&& id",
           "\nid", "quick;id", "quick id", "QUICK", "on;id", "on off", "é", "a" * 5000]
BAD_NAMES = [h for h in HOSTILE if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,127}", h)]
for h in HOSTILE:
    refuses("evenkeel-os-tools-admin", [h])
    refuses("evenkeel-os-tools-admin", ["updates", h])
    refuses("evenkeel-os-tools-admin", ["test-rollback", h])
    refuses("evenkeel-os-tools-admin", ["disk-unlock", h])
    refuses("evenkeel-os-tools-safe", [h])
    refuses("evenkeel-os-tools-safe", ["updates", h])
    refuses("evenkeel-os-tools-safe", ["disk-unlock", h])
    refuses("evenkeel-os-codecs-setup", [h])
    refuses("evenkeel-os-codecs-admin", [h])
for h in BAD_NAMES:
    refuses("evenkeel-os-hwrules", ["remove", h])
    refuses("evenkeel-os-hwrules", ["add", h, "/dev/null"])
refuses("evenkeel-os-hwrules", ["add", "pkg", "/dev/null"], codes=(1,))
refuses("evenkeel-os-tools-admin", ["updates", "on", "extra"])
refuses("evenkeel-os-tools-admin", ["test-rollback", "quick", "extra"])
refuses("evenkeel-os-codecs-setup", ["web", "full"])
refuses("evenkeel-os-hwrules", ["add", "pkg"])

# The hardware-rules helper, loaded as a module with its rule folder pointed at a scratch folder.
loader = importlib.machinery.SourceFileLoader("hwrules", str(LIBEXEC / "evenkeel-os-hwrules"))
hw = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(hw)
hw.reload = lambda: None
with tempfile.TemporaryDirectory() as d:
    hw.RULES = Path(d, "rules.d")
    src = Path(d, "src")
    src.mkdir()

    def add(name, text=None, link=None, fifo=False):
        f = src / name
        if link:
            f.symlink_to(link)
        elif fifo:
            os.mkfifo(f)
        else:
            f.write_text(text)
        try:
            hw.add("test-pkg", [str(f)])
            return True
        except SystemExit:
            return False
        finally:
            f.unlink()

    must_refuse = {
        "a shortcut to a private file": ("link.rules", None, "/etc/shadow", False),
        "a shortcut to a rule file": ("link2.rules", None, "/usr/lib/udev/rules.d/50-udev-default.rules", False),
        "a pipe instead of a file": ("pipe.rules", None, None, True),
        "a name that isn't a rule file": ("evil.sh", 'SUBSYSTEM=="usb", MODE="0666"\n', None, False),
        "a rule that runs a program": ("run.rules", 'SUBSYSTEM=="usb", RUN+="/bin/sh -c id"\n', None, False),
        "a program split over lines": ("run2.rules", 'SUBSYSTEM=="usb", \\\nRUN+="/x"\n', None, False),
        "a disk opened to everyone": ("disk.rules", 'KERNEL=="sd*", MODE="0666"\n', None, False),
        "a disk given to a group": ("disk2.rules", 'SUBSYSTEM=="block", GROUP="users"\n', None, False),
        "a disk handed to the logged-in user": ("disk3.rules", 'SUBSYSTEM=="block", TAG+="uaccess"\n', None, False),
        "storage hidden among USB": ("disk4.rules", 'SUBSYSTEM=="usb|block", MODE="0666"\n', None, False),
        "every device at once": ("all.rules", 'MODE="0666"\n', None, False),
        "an owner change with no device kind": ("own.rules", 'KERNEL=="nvme0n1", OWNER="nobody"\n', None, False),
        "a guard for a disallowed kind": ("guard.rules", 'SUBSYSTEM!="block", GOTO="end"\nMODE="0666"\nLABEL="end"\n',
                                          None, False),
        "every USB disk, matched by its USB parent": ("usbdisk.rules", 'SUBSYSTEMS=="usb", MODE="0666"\n', None, False),
        "any device with a given product name": ("prod.rules", 'ATTRS{product}=="*Flash*", MODE="0666"\n', None, False),
        "the disk-mapper control": ("dm.rules", 'SUBSYSTEM=="misc", KERNEL=="device-mapper", MODE="0666"\n', None,
                                    False),
        "every keyboard, read raw": ("keys.rules", 'SUBSYSTEM=="hidraw", TAG+="uaccess"\n', None, False),
        "every keyboard and mouse": ("input.rules", 'SUBSYSTEM=="input", MODE="0666"\n', None, False),
        "every input device, by name": ("event.rules", 'KERNEL=="event*", GROUP="users", MODE="0660"\n', None, False),
        "every USB device behind a guard": ("allusb.rules", 'SUBSYSTEM!="usb", GOTO="e"\nMODE="0666"\nLABEL="e"\n',
                                            None, False),
        "a flag that isn't tied to one maker": ("flag.rules", 'SUBSYSTEM=="hidraw", ENV{k}="1"\n'
                                                'ENV{k}=="1", TAG+="uaccess"\n', None, False),
        "every misc device": ("misc.rules", 'SUBSYSTEM=="misc", TAG+="uaccess"\n', None, False),
        "access after the guard ends": ("guard2.rules", 'SUBSYSTEM!="usb", GOTO="end"\nLABEL="end"\n'
                                        'KERNEL=="sd*", MODE="0666"\n', None, False),
    }
    for why, (name, text, link, fifo) in must_refuse.items():
        if add(name, text, link, fifo):
            bad(f"the hardware-rules helper added {why}")
    must_take = {
        "a USB device for its users": ('SUBSYSTEM=="usb", ATTR{idVendor}=="1234", MODE="0666"\n'),
        "a controller for the logged-in user": ('SUBSYSTEM=="hidraw", ATTRS{idVendor}=="28de", TAG+="uaccess"\n'),
        "a phone, behind a USB guard": ('SUBSYSTEM!="usb", GOTO="phone_end"\nATTR{idVendor}=="18d1", MODE="0666"\n'
                                        'LABEL="phone_end"\n'),
        "a controller matched by name only": ('KERNEL=="hidraw*", ATTRS{idVendor}=="28de", MODE="0660"\n'),
        "one USB device, by its vendor": ('ATTRS{idVendor}=="0483", ATTRS{idProduct}=="3748", MODE="0666"\n'),
        "virtual controllers (uinput)": ('KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess"\n'),
        "one maker's receivers (like Solaar)": ('SUBSYSTEM=="hidraw", ATTRS{idVendor}=="046d", TAG+="uaccess"\n'),
        "a flag set for one maker": ('SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", ENV{p}="1"\n'
                                     'ENV{p}=="1", TAG+="uaccess"\n'),
        "a controller by its kernel name": ('SUBSYSTEM=="hidraw", KERNELS=="0005:28DE:*", MODE="0660"\n'),
        "a serial adapter": ('SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", GROUP="dialout", MODE="0660"\n'),
        "a match-only rule": ('SUBSYSTEM=="usb", ATTR{idVendor}=="1234", ENV{ID_TEST}="1"\n'),
    }
    for i, (why, text) in enumerate(must_take.items()):
        if not add(f"ok{i}.rules", text):
            bad(f"the hardware-rules helper refused {why}")
    if any(p.is_symlink() for p in hw.RULES.glob("*")) or not all(
            p.read_text().startswith("# evenkeel-os-package: test-pkg\n") for p in hw.RULES.glob("*.rules")):
        bad("the hardware-rules helper wrote something other than marked rule files")

# Permissions: anything that needs no password is for the person at the computer only.
for f in sorted(RULES_D.glob("*evenkeel-os*.rules")):
    t = f.read_text()
    if "Result.YES" in t and not re.search(r"subject\.local\s*&&\s*subject\.active", t):
        bad(f"{f.name} lets someone not at the computer act without a password")
uupd = RULES_D / "uupd.rules"
guard = RULES_D / "40-evenkeel-os-uupd.rules"
if uupd.exists():
    if not guard.exists() or not guard.name < uupd.name:
        bad("uupd's rule (any account starts, stops or restarts updates) isn't narrowed by 40-evenkeel-os-uupd.rules")
    elif not all(k in guard.read_text() for k in ('subject.local && subject.active', 'verb == "start"',
                                                   'verb == "stop"', "Result.AUTH_ADMIN")):
        bad("40-evenkeel-os-uupd.rules no longer limits updates to start and stop at the computer")
for f in sorted(ACTIONS.glob("io.github.ctsdownloads.evenkeel-os.*.policy")):
    t = f.read_text()
    for kind in ("allow_any", "allow_inactive"):
        for v in re.findall(rf"<{kind}>([^<]*)</{kind}>", t):
            if v not in ("no", "auth_admin", "auth_admin_keep"):
                bad(f"{f.name}: {kind} is {v}, so someone not at the computer could act")
    for v in re.findall(r"<allow_active>([^<]*)</allow_active>", t):
        if v not in ("auth_admin", "auth_admin_keep"):
            bad(f"{f.name}: allow_active is {v}; a no-password action needs a rule limited to the computer")

if problems:
    print("ERROR: root helper or permission check failed:")
    for p in problems:
        print(f"  - {p}")
    sys.exit(1)
print(f"Root helpers: {len(HOSTILE)} hostile inputs refused by every helper, {len(must_refuse)} bad hardware rules "
      f"refused, {len(must_take)} good ones kept; no-password permissions are for the person at the computer only")
