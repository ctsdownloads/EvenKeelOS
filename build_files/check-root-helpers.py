#!/usr/bin/python3 -I
"""Build check: the root helpers refuse hostile input, and no-password permissions stay at the computer only."""
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
    refuses("evenkeel-os-tools-admin", ["firewall", h, "on"])
    refuses("evenkeel-os-tools-admin", ["firewall", "ssh", h])
    refuses("evenkeel-os-tools-admin", ["sharing", h])
    refuses("evenkeel-os-tools-admin", ["sharing", "add", "/root", h])
    refuses("evenkeel-os-tools-admin", ["sharing", "add", h, "ro"], codes=(1,))     # no caller: refused first
    refuses("evenkeel-os-tools-admin", ["sharing", "remove", h], codes=(1,))
    refuses("evenkeel-os-tools-admin", ["test-settings"])
    refuses("evenkeel-os-settings-test", [h])
    refuses("evenkeel-os-cert-remove", [h, "a" * 64], codes=(1, 2))    # names that pass are files that don't exist
    refuses("evenkeel-os-cert-remove", ["a.pem", h])
    refuses("evenkeel-os-settings", [h])
    refuses("evenkeel-os-settings", ["save", h])
    refuses("evenkeel-os-tools-safe", [h])
    refuses("evenkeel-os-tools-safe", ["updates", h])
    refuses("evenkeel-os-tools-safe", ["disk-unlock", h])
    refuses("evenkeel-os-codecs-setup", [h])
    refuses("evenkeel-os-codecs-admin", [h])
    for verb in ("install", "turn-on", "remove"):
        refuses("evenkeel-os-vpn", [verb, h])
    refuses("evenkeel-os-vpn", [h])
for h in BAD_NAMES:
    refuses("evenkeel-os-vpn", ["services", h])
    refuses("evenkeel-os-hwrules", ["remove", h])
    refuses("evenkeel-os-hwrules", ["add", h, "/dev/null"])
refuses("evenkeel-os-hwrules", ["add", "pkg", "/dev/null"], codes=(1,))
refuses("evenkeel-os-tools-admin", ["updates", "on", "extra"])
refuses("evenkeel-os-tools-admin", ["test-rollback", "quick", "extra"])
refuses("evenkeel-os-tools-admin", ["keep-update", "extra"])
refuses("evenkeel-os-tools-admin", ["keep-update"], codes=(1,))     # no startup check is asking
for args in (["firewall", "samba", "on"], ["firewall", "ssh", "maybe"], ["firewall", "ssh"],
             ["firewall", "ssh", "on", "x"], ["firewall", "--zone=public", "on"], ["firewall", "ssh;id", "on"],
             ["firewall", "default", "x"]):
    refuses("evenkeel-os-tools-admin", args)
for args in (["sharing"], ["sharing", "on", "x"], ["sharing", "add", "/root"], ["sharing", "mode", "/root"],
             ["sharing", "remove"], ["sharing", "password", "x"], ["sharing", "sync", "x"],
             ["sharing", "add", "/root", "ro", "x"]):
    refuses("evenkeel-os-tools-admin", args)
for args in (["let-in"], ["let-in", "home"], ["let-in", "office", "app", "ssh"], ["let-in", "home", "app"],
             ["let-in", "home", "open", "ssh"], ["let-in", "home", "app", "ssh", "x"], ["let-in", "home", "ports", "A"],
             ["let-in", "update", "x"], ["let-in", "--zone=trusted", "app", "ssh"]):
    refuses("evenkeel-os-tools-admin", args)
# Refused before the firewall is touched: not on the list, always let in, a switch's job, a bad name or port.
for args in (["let-in", "home", "app", "../../etc/x"], ["let-in", "home", "app", "no-such-app"],
             ["let-in", "work", "app", "evenkeel-sharing"], ["let-in", "public", "app", "mdns"],
             ["let-in", "home", "app", "ssh"], ["let-in", "home", "app", "ipp"],
             ["let-in", "work", "ports", "", "80/tcp"], ["let-in", "work", "ports", "x" * 61, "80/tcp"],
             ["let-in", "work", "ports", "Game", "0/tcp"], ["let-in", "work", "ports", "Game", "80/sctp"],
             ["let-in", "work", "ports", "Game", "80/tcp", "80/tcp"], ["let-in", "work", "ports", "Game", "80/tcp;id"],
             ["let-in", "home", "remove", "ssh"], ["let-in", "home", "remove", "ports:1/tcp"],
             ["let-in", "work", "app", "samba"], ["let-in", "public", "app", "ws-discovery"],
             ["let-in", "work", "app", "freeipa-trust"], ["let-in", "public", "app", "samba-client"],
             ["let-in", "work", "ports", "Files", "445/tcp"], ["let-in", "public", "ports", "All", "1-65535/udp"]):
    refuses("evenkeel-os-tools-admin", args, codes=(3,))
refuses("evenkeel-os-tools-admin", ["sharing", "on"], codes=(1,))              # no caller, or not set up: refused
refuses("evenkeel-os-tools-admin", ["sharing", "password"], codes=(1,))
for bad_setting in ("root=/dev/sda1", "ostree=/x", "rw", "rd.luks.uuid=x", "evenkeel_os.test_rollback=quick",
                    "init=/bin/sh", "rdinit=/x", "systemd.run=/x", "--source=x", "-x", "a b",
                    "a;id", "$(id)", "\nid", "é=1", "", "x" * 65, 'a="b c"'):
    refuses("evenkeel-os-boot-options", ["set", "amdgpu.abmlevel=0", bad_setting], codes=(3,))
refuses("evenkeel-os-boot-options", ["set", "a=1", "a=2"], codes=(3,))       # one name, two values
refuses("evenkeel-os-boot-options", ["set", "a-b=1", "a_b=2"], codes=(3,))   # the same name to the kernel
refuses("evenkeel-os-boot-options", ["set", *[f"a{n}=1" for n in range(21)]], codes=(3,))
for args in ([], ["add", "x"], ["--help"], ["set;id"]):
    refuses("evenkeel-os-boot-options", args)
for args in (["sharing", "password"], ["sharing", "add", "/root", "rw"], ["sharing", "on"]):    # root can't share
    r = subprocess.run([str(LIBEXEC / "evenkeel-os-tools-admin"), *args], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, env={**os.environ, "PKEXEC_UID": "0"}, timeout=60)
    if r.returncode != 1:
        bad(f"evenkeel-os-tools-admin {args!r} as root exited {r.returncode}: root could share folders")
refuses("evenkeel-os-settings", ["check", "--own-namespace"])
refuses("evenkeel-os-settings", ["test-delete", "extra"])
refuses("evenkeel-os-cert-remove", ["no-such-certificate.pem", "a" * 64], codes=(1,))
refuses("evenkeel-os-cert-remove", ["..", "a" * 64])
refuses("evenkeel-os-cert-remove", ["../../shadow", "a" * 64])
refuses("evenkeel-os-cert-remove", ["a.pem"])
refuses("evenkeel-os-cert-remove", ["a.pem", "a" * 64 + "\n"])


def cert_remove_refusals():
    """What evenkeel-os-cert-remove must leave alone, set up in the real anchors folder and taken out again."""
    import datetime
    import hashlib
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import Encoding

    def make(n):
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, n)])
        now = datetime.datetime.now(datetime.timezone.utc)
        return (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                .serial_number(1).not_valid_before(now).not_valid_after(now + datetime.timedelta(days=1))
                .sign(key, hashes.SHA256()))
    one, two = make("Check one"), make("Check two")
    fp = hashlib.sha256(one.public_bytes(Encoding.DER)).hexdigest()
    anchors = Path("/etc/pki/ca-trust/source/anchors")
    made = {"evenkeel-check-two.pem": one.public_bytes(Encoding.PEM) + two.public_bytes(Encoding.PEM),
            "evenkeel-check-other.pem": two.public_bytes(Encoding.PEM)}
    try:
        for name, data in made.items():
            (anchors / name).write_bytes(data)
        os.symlink("/etc/shadow", anchors / "evenkeel-check-link.pem")
        os.mkfifo(anchors / "evenkeel-check-pipe.pem")
        refuses("evenkeel-os-cert-remove", ["evenkeel-check-two.pem", fp], codes=(3,))
        refuses("evenkeel-os-cert-remove", ["evenkeel-check-other.pem", fp], codes=(3,))
        refuses("evenkeel-os-cert-remove", ["evenkeel-check-link.pem", fp], codes=(1,))
        refuses("evenkeel-os-cert-remove", ["evenkeel-check-pipe.pem", fp], codes=(1,))
        if not all((anchors / n).exists() for n in made) or not (anchors / "evenkeel-check-link.pem").is_symlink():
            bad("evenkeel-os-cert-remove removed a file it should have left alone")
    finally:
        for n in (*made, "evenkeel-check-link.pem", "evenkeel-check-pipe.pem"):
            (anchors / n).unlink(missing_ok=True)


cert_remove_refusals()
# Wheelhouse offers "Remove it" only for names the helper takes.
patterns = [re.search(r'(?m)^(?:CERT_FILE|NAME) = re\.compile\((r".*?")\)', Path(f).read_text())
            for f in ("/usr/bin/evenkeel-os-tools", "/usr/libexec/evenkeel-os-cert-remove")]
if not all(patterns) or patterns[0].group(1) != patterns[1].group(1):
    bad("Wheelhouse and evenkeel-os-cert-remove don't take the same certificate file names")
refuses("evenkeel-os-tools-admin", ["cert-remove", "a.pem"])
refuses("evenkeel-os-codecs-setup", ["web", "full"])
refuses("evenkeel-os-hwrules", ["add", "pkg"])
refuses("evenkeel-os-vpn", ["install", "mullvad", "extra"])
refuses("evenkeel-os-vpn", ["services", "pkg", "extra"])
refuses("evenkeel-os-vpn", ["services", "not-added-to-the-system"], codes=(1,))

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

# Settings test, certificate removal and boot options: no rule may skip the password.
policy = (ACTIONS / "io.github.ctsdownloads.evenkeel-os.tools.policy").read_text()
for name, helper in (("settings-test", "evenkeel-os-settings-test"), ("cert-remove", "evenkeel-os-cert-remove"),
                     ("boot-options", "evenkeel-os-boot-options")):
    m = re.search(rf'<action id="io\.github\.ctsdownloads\.evenkeel-os\.{name}">(.*?)</action>', policy, re.S)
    if not m or f"/usr/libexec/{helper}</annotate>" not in m.group(1):
        bad(f"{helper} has no polkit action of its own")
    elif sorted(re.findall(r"<allow_\w+>([^<]*)</allow_\w+>", m.group(1))) != ["auth_admin"] * 3:
        bad(f"{helper}'s polkit action doesn't ask for the admin password every time")
RULE_FILES = sorted([*RULES_D.glob("*.rules"), *Path("/etc/polkit-1/rules.d").glob("*.rules")])
for f in RULE_FILES:
    t = f.read_text()
    # Our actions may only be named whole (action.id == "..."); any other use could match several at once.
    rest = re.sub(r'action\.id\s*===?\s*"io\.github\.ctsdownloads\.evenkeel-os\.[a-z0-9.-]+"', "", t)
    if "settings-test" in t or "cert-remove" in t or "boot-options" in t or "ctsdownloads" in rest:
        bad(f"{f} could cover the settings test's, certificate removal's or boot options' polkit action")
    # A rule that says yes without naming any action says yes to everything, ours included.
    if "Result.YES" in t and "action.id" not in t and f.name != "empower.rules":
        bad(f"{f} says yes to every action")
# systemd's empower.rules says yes to everything for its "empower" group (run0 --empower): nobody may be in it.
for line in [*Path("/etc/group").read_text().splitlines(), *Path("/usr/lib/group").read_text().splitlines()]:
    f = line.split(":")
    if f[0] == "empower" and len(f) > 3 and f[3].strip():
        bad(f"the empower group has members ({f[3]}): they could do anything without a password")

if problems:
    print("ERROR: root helper or permission check failed:")
    for p in problems:
        print(f"  - {p}")
    sys.exit(1)
print(f"Root helpers: {len(HOSTILE)} hostile inputs refused by every helper, {len(must_refuse)} bad hardware rules "
      f"refused, {len(must_take)} good ones kept; no-password permissions are for the person at the computer only")
