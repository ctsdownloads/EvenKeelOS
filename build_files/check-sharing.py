#!/usr/bin/python3 -I
"""Build check for Shared folders: Samba shares only what Wheelhouse lists, and only from the home folder."""
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, "/usr/lib/evenkeel-os")
import evenkeel_os_sharing as sharing  # noqa: E402

problems = []


def bad(msg):
    problems.append(msg)


def testparm(conf):
    r = subprocess.run(["testparm", "-s", "-v", str(conf)], capture_output=True, text=True)
    if r.returncode != 0 or "Unknown parameter" in r.stderr or "Ignoring unknown" in r.stderr:
        bad(f"testparm doesn't take {conf}: {r.stderr.strip()}")
    return {k.strip().lower(): v.strip() for k, _, v in (line.partition("=") for line in r.stdout.splitlines())
            if _}


if not sharing.set_up():
    bad(f"{sharing.SMB_CONF} doesn't include {sharing.SHARES}")
g = testparm(sharing.SMB_CONF)
for key, want in {"map to guest": "Never", "disable netbios": "Yes", "multicast dns register": "Yes",
                  "load printers": "No", "server min protocol": "SMB2", "server smb transports": "445",
                  "restrict anonymous": "2", "map archive": "No",
                  "mdns name": "mdns"}.items():
    if g.get(key) != want:
        bad(f"smb.conf: {key} is {g.get(key)!r}, not {want!r}")
if "[homes]" in sharing.SMB_CONF.read_text() or "usershare" in sharing.SMB_CONF.read_text():
    bad("smb.conf shares home folders or user shares on its own")
if subprocess.run(["systemctl", "is-enabled", "avahi-daemon.service"], capture_output=True,
                  text=True).stdout.strip() != "enabled":
    bad("avahi-daemon isn't on: Macs and Linux computers couldn't find this computer")

r = subprocess.run(["firewall-offline-cmd", f"--info-service={sharing.FIREWALL_SERVICE}"], capture_output=True,
                   text=True)
info = {k.strip(): v.strip() for k, _, v in (line.partition(":") for line in r.stdout.splitlines()) if _}
if info.get("ports") != "445/tcp" or info.get("includes") != "wsdd":
    bad(f"the {sharing.FIREWALL_SERVICE} firewall service is {info}, not 445/tcp plus wsdd")

unit = Path("/usr/lib/systemd/system/wsdd.service").read_text()
dropin = Path("/usr/lib/systemd/system/wsdd.service.d/50-evenkeel-os.conf")
if "$OPTIONS" not in unit or not dropin.exists() or "EnvironmentFile=-/run/evenkeel-os/wsdd" not in dropin.read_text():
    bad("wsdd wouldn't be held to Home networks: its unit or our drop-in changed")
hook = Path("/usr/lib/NetworkManager/dispatcher.d/50-evenkeel-os-sharing")
st = hook.stat() if hook.exists() else None
if not st or st.st_uid != 0 or st.st_mode & 0o022 or not st.st_mode & stat.S_IXUSR:
    bad("NetworkManager won't run the Shared folders hook (missing, not root's, writable by others, or not runnable)")
if not any(b"samba_enable_home_dirs" in f.read_bytes() for f in Path("/etc/selinux/targeted/policy").glob("policy.*")):
    bad("SELinux has no samba_enable_home_dirs switch")

real_getpwnam = sharing.pwd.getpwnam
with tempfile.TemporaryDirectory() as scratch:
    # A made-up person whose home is a scratch folder: the image's own home folders don't exist while it's built.
    home = os.path.join(os.path.realpath(scratch), "home")
    d = os.path.join(home, "work")
    os.makedirs(d)
    sharing.pwd.getpwnam = lambda name: (real_getpwnam(name) if name != "tester" else
                                         SimpleNamespace(pw_dir=home, pw_uid=os.getuid()))
    pics = os.path.join(d, "Pictures")
    os.mkdir(pics)
    Path(d, "file.txt").write_text("x")
    os.mkdir(os.path.join(d, ".ssh"))
    os.symlink(pics, os.path.join(d, "link"))
    latin = os.path.join(d, "caf\udce9")
    os.mkdir(latin)
    theirs = os.path.join(d, "Theirs")
    os.mkdir(theirs)
    os.chown(theirs, 65534, 65534)
    cases = {pics: True, latin: False, home: False, os.path.join(d, ".ssh"): False, "/etc": False,
             os.path.join(d, "file.txt"): False, os.path.join(d, "link"): False, os.path.join(d, "nothing"): False,
             d + "/../" + os.path.basename(d): False, scratch: False, theirs: False}
    for path, ok in cases.items():
        if (sharing.folder_problem(path, "tester") == "") != ok:
            bad(f"{path} {'can' if not ok else 'can not'} be shared")
    sharing.pwd.getpwnam = real_getpwnam
    names = {"Pictures": "Pictures", "a[b]:c": "a b c", "homes": "homes folder", "%U": "U", "": "Shared folder"}
    for base, want in names.items():
        if sharing.share_name("/x/" + base, []) != want:
            bad(f"a folder named {base!r} is shared as {sharing.share_name('/x/' + base, [])!r}, not {want!r}")
    if sharing.share_name("/x/Pictures", ["pictures", "Pictures 2"]) != "Pictures 3":
        bad("two folders with the same name get the same share name")
    state = {"on": True, "passwords": ["root"], "folders": [
        {"path": pics, "owner": "root", "mode": "ro", "name": "Pictures"},
        {"path": pics, "owner": "nobody-with-no-password", "mode": "rw", "name": "Other"}]}
    conf = Path(d, "smb.conf")
    conf.write_text("[global]\n\tmap to guest = Never\n" + sharing.shares_conf(state))
    shares = subprocess.run(["testparm", "-s", str(conf)], capture_output=True, text=True).stdout
    if "[Pictures]" not in shares or "valid users = root" not in shares or "[Other]" in shares:
        bad(f"the shares written for Wheelhouse's list aren't what it says:\n{shares}")
    if "read only = No" in shares:
        bad("a read-only folder was shared for writing")

if problems:
    print("ERROR: Shared folders isn't set up right:\n  " + "\n  ".join(problems))
    sys.exit(1)
print("Shared folders: guest access off, nothing shared until picked, found by Windows and Macs, home folders only")
