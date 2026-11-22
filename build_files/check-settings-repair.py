#!/usr/bin/python3 -I
"""Build check: the settings repair finds broken important settings and puts back exactly those.

Runs evenkeel-os-settings' check and restore against a made-up /etc, saved copy, default settings and systemd
factory files in a scratch folder (systemd copies its generic files in at boot, before greenboot), then checks that
greenboot runs each step from the right folder.
"""
import importlib.machinery
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

HELPER = Path(sys.argv[1] if len(sys.argv) > 1 else "/usr/libexec/evenkeel-os-settings")
GB = Path(sys.argv[2] if len(sys.argv) > 2 else "/usr/lib/greenboot")
DROPIN = Path(sys.argv[3] if len(sys.argv) > 3 else
              "/usr/lib/systemd/system/greenboot-healthcheck.service.d/50-evenkeel-os.conf")
TMPFILES = Path(sys.argv[4] if len(sys.argv) > 4 else "/usr/lib/tmpfiles.d")


def die(msg):
    sys.exit(f"ERROR: settings repair: {msg}")


loader = importlib.machinery.SourceFileLoader("settings", str(HELPER))
spec = importlib.util.spec_from_loader("settings", loader)
st = importlib.util.module_from_spec(spec)
loader.exec_module(st)

DENY = "auth required pam_deny.so\n"
FILES = {"passwd": "root:x:0:0:root:/root:/bin/bash\nmatt:x:1000:1000:Matt:/var/home/matt:/bin/bash\n",
         "shadow": "root:!::0:99999:7:::\nmatt:$y$x::0:99999:7:::\n", "group": "root:x:0:\nmatt:x:1000:\n",
         "gshadow": "root:::\nmatt:!::\n", "fstab": "UUID=0f-1 /boot ext4 ro 0 0\n", "sudoers": "root ALL=(ALL) ALL\n",
         "pam.d/login": "auth include system-auth\n", "pam.d/sudo": "auth include system-auth\n",
         "pam.d/other": DENY, "authselect/system-auth": "auth sufficient pam_fprintd.so\n",
         "authselect/nsswitch.conf": "passwd: files altfiles systemd\n",
         "pki/tls/cert.pem": "shipped\n", "pki/ca-trust/source/anchors/mine.pem": "added by the person\n",
         "sudoers.d/grant": "matt ALL=(ALL) ALL\n", "locale.conf": "LANG=en_GB.UTF-8\n",
         "vconsole.conf": "KEYMAP=uk\n", "selinux/config": "SELINUX=enforcing\n",
         "selinux/targeted/policy/policy.35": "policy\n", "selinux/targeted/contexts/files/file_contexts": "ctx\n",
         "NetworkManager/system-connections/home.nmconnection": "[connection]\n"}
LINKS = {"pam.d/system-auth": "../authselect/system-auth", "nsswitch.conf": "authselect/nsswitch.conf"}
SHIPS = ["pam.d", "pam.d/login", "pam.d/sudo", "pam.d/other", "pam.d/system-auth", "authselect",
         "authselect/system-auth", "authselect/nsswitch.conf", "pki", "pki/tls", "pki/tls/cert.pem", "nsswitch.conf",
         "selinux", "selinux/config", "selinux/targeted"]
GENERIC = {"pam.d/other": "auth include system-auth\n", "pam.d/system-auth": "auth required pam_unix.so\n",
           "nsswitch.conf": "passwd: files systemd\n", "locale.conf": "LANG=C.UTF-8\n", "vconsole.conf": "KEYMAP=us\n"}
MODES = {"shadow": 0o000, "gshadow": 0o000, "sudoers": 0o440, "sudoers.d/grant": 0o440,
         "NetworkManager/system-connections/home.nmconnection": 0o600}


def write(root, files):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        os.chmod(p, MODES.get(rel, 0o644))


def tmpfiles(etc, factory):
    """What systemd-tmpfiles' C! lines do at boot: copy in the generic file when it's missing."""
    for rel in ("pam.d", "nsswitch.conf", "locale.conf", "vconsole.conf"):
        if not os.path.lexists(etc / rel):
            src = factory / rel
            shutil.copytree(src, etc / rel) if src.is_dir() else shutil.copy2(src, etc / rel)


def main():
    if set(st.TEST_DELETE) - set(st.CORE_FILES + st.CORE_DIRS):
        die("the test deletes settings the start-up check doesn't look for")
    # Every setting systemd replaces with its generic copy at boot has to be checked (issue is only the login text).
    rebuilt = {m.group(1) for f in sorted(TMPFILES.glob("*.conf"))
               for m in re.finditer(r"^C[+!]*\s+/etc/(\S+)", f.read_text(), re.M)} - {"issue"}
    if rebuilt - set(st.CORE_FILES + st.CORE_DIRS):
        die(f"systemd puts generic copies of {sorted(rebuilt - set(st.CORE_FILES + st.CORE_DIRS))} in place at boot, "
            "and the check doesn't look at them")
    if "sudoers.d" in st.CORE_FILES + st.CORE_DIRS:
        die("sudoers.d is put back: a removed admin grant would come back")
    if st.shown(["pam.d/login", "pam.d/sudo", "fstab", "selinux/targeted"]) != ["pam.d", "fstab", "selinux/targeted"]:
        die("a folder put back isn't counted as one")
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        etc, saved, usr_etc, factory = d / "etc", d / "saved", d / "usr-etc", d / "factory"
        write(etc, FILES)
        for rel, target in LINKS.items():
            os.symlink(target, etc / rel)
        for rel in SHIPS:
            (usr_etc / rel).parent.mkdir(parents=True, exist_ok=True)
            if rel in ("pam.d", "authselect", "pki", "pki/tls", "selinux", "selinux/targeted"):
                (usr_etc / rel).mkdir(exist_ok=True)
            else:
                (usr_etc / rel).write_text("")
        write(factory, GENERIC)
        if st.check(saved, etc, usr_etc, factory) != 0:
            die("with no saved copy yet, the start fails")
        saved.mkdir()
        subprocess.run([*st.RSYNC, f"{etc}/", f"{saved / 'etc'}/"], check=True)
        (saved / "usr-etc.list").write_text("\n".join(SHIPS) + "\n")
        (saved / "saved").write_text("x 1\n")
        if st.check(saved, etc, usr_etc, factory) != 0:
            die("with nothing broken, the start fails")
        # What people may remove stays removed: their own files, admin grants, Wi-Fi networks.
        for rel in ("pki/ca-trust/source/anchors/mine.pem", "sudoers.d/grant",
                    "NetworkManager/system-connections/home.nmconnection", "pki/tls/cert.pem"):
            (etc / rel).unlink()
        if st.check(saved, etc, usr_etc, factory) != 0 or st.restore(saved, etc, usr_etc, factory)[0]:
            die("removing a certificate (added or shipped), an admin grant or a Wi-Fi network fails the start or "
                "comes back")
        # The test's deletions plus the language and keyboard files, then the boot: systemd's generic copies.
        for n in (*st.TEST_DELETE, "locale.conf", "vconsole.conf"):
            subprocess.run(["rm", "-rf", str(etc / n)], check=True)
        tmpfiles(etc, factory)
        want = {"fstab", "passwd", "shadow", "group", "gshadow", "sudoers", "pam.d/login", "pam.d/sudo",
                "pam.d/other", "pam.d/system-auth", "locale.conf", "vconsole.conf"}
        got = set(st.broken(saved, etc, usr_etc, factory))
        if got != want:
            die(f"the start-up check finds {sorted(got)} broken, not {sorted(want)}")
        if st.check(saved, etc, usr_etc, factory) != 1:
            die("the start doesn't fail with important settings broken")
        put, errors = st.restore(saved, etc, usr_etc, factory)
        if errors or set(put) != want:
            die(f"the repair put back {sorted(put)} (errors {errors}), not {sorted(want)}")
        for rel, text in FILES.items():
            if os.path.exists(saved / "etc" / rel) and os.path.exists(etc / rel) and (
                    (etc / rel).read_text() != text or (etc / rel).stat().st_mode & 0o7777 != MODES.get(rel, 0o644)):
                die(f"{rel} didn't come back the same (content or permissions)")
        if (etc / "pam.d/other").read_text() != DENY:
            die("pam.d/other stays systemd's generic one, which lets programs without their own rules log in")
        if os.readlink(etc / "pam.d/system-auth") != LINKS["pam.d/system-auth"]:
            die("pam.d/system-auth doesn't come back as the link to authselect's")
        for rel in ("pki/ca-trust/source/anchors/mine.pem", "sudoers.d/grant",
                    "NetworkManager/system-connections/home.nmconnection", "pki/tls/cert.pem"):
            if os.path.lexists(etc / rel):
                die(f"the repair put back {rel}, which was removed on purpose")
        if st.check(saved, etc, usr_etc, factory) != 0:
            die("after the repair, the start still fails")
        # Without its policy folder, an enforcing start freezes: the whole folder comes back.
        subprocess.run(["rm", "-rf", str(etc / "selinux/targeted")], check=True)
        put, errors = st.restore(saved, etc, usr_etc, factory)
        if errors or put != ["selinux/targeted"] or \
                (etc / "selinux/targeted/policy/policy.35").read_text() != FILES["selinux/targeted/policy/policy.35"]:
            die(f"a missing SELinux policy folder isn't put back whole ({put}, {errors})")
        # A generic nsswitch.conf (no altfiles: system accounts can't be found) is replaced by the saved link.
        (etc / "nsswitch.conf").unlink()
        tmpfiles(etc, factory)
        put, errors = st.restore(saved, etc, usr_etc, factory)
        if put != ["nsswitch.conf"] or os.readlink(etc / "nsswitch.conf") != LINKS["nsswitch.conf"]:
            die(f"systemd's generic nsswitch.conf isn't replaced by the saved one ({put}, {errors})")
        # What's there is never replaced: changed settings, and accounts removed on purpose (old passwords included).
        (etc / "sudoers").write_text("changed\n")
        (etc / "passwd").write_text("root:x:0:0:root:/root:/bin/bash\n")
        if st.check(saved, etc, usr_etc, factory) != 0 or st.restore(saved, etc, usr_etc, factory)[0]:
            die("a changed setting or removed accounts fail the start or come back")
        if (etc / "sudoers").read_text() != "changed\n" or "matt" in (etc / "passwd").read_text():
            die("the repair replaced a setting someone changed")
    # One retry per saved copy, so settings broken at every start still reach the earlier version (run last).
    with tempfile.TemporaryDirectory() as d:
        calls = []

        class Done:
            returncode, stdout = 0, ""
        st.own_namespace, st.grubenv, st.RETRIED = (lambda: True), (lambda: ["boot_counter=0"]), Path(d, "retried")
        st.subprocess = types.SimpleNamespace(run=lambda a, **k: calls.append(a) or Done())
        for saved_time in (5, 5, 6):
            st.start_counter(saved_time)
        if sum("boot_counter=1" in c for c in calls) != 2:
            die("a repair adds a retry more than once for the same saved copy (it could restart forever)")
    if "machine-id" in st.CORE_FILES:
        die("machine-id is checked: systemd makes a new one when it's missing, so it can't be put back")
    steps = {GB / "check/required.d/05-evenkeel-os-settings.sh": "check",
             GB / "red.d/50-evenkeel-os-settings-repair.sh": "repair",
             GB / "green.d/95-evenkeel-os-settings-save.sh": "save"}
    for f, job in steps.items():
        if f"exec /usr/libexec/evenkeel-os-settings {job}\n" not in f.read_text() or not os.access(f, os.X_OK):
            die(f"{f} doesn't run evenkeel-os-settings {job}")
    first = sorted(p.name for p in (GB / "check/required.d").iterdir())
    if first[:2] != ["00-evenkeel-os-test-quick.sh", "05-evenkeel-os-settings.sh"]:
        die(f"the settings check isn't the first real check: {first}")
    if sorted(p.name for p in (GB / "green.d").iterdir())[-1] != "95-evenkeel-os-settings-save.sh":
        die("the save isn't the last good-start step, so the rollback note can't see the settings test's marker")
    if "ExecStartPre=/usr/bin/mkdir -p /etc/motd.d\n" not in DROPIN.read_text():
        die(f"{DROPIN} doesn't make /etc/motd.d before greenboot starts")
    print(f"Settings repair: the check finds {len(want)} broken important settings (missing, or "
          "systemd's generic copies), the repair puts back exactly those and a missing SELinux policy whole, "
          "certificates and files people remove stay removed, nothing changed is replaced; greenboot runs check, "
          "repair and save")


if __name__ == "__main__":
    main()
