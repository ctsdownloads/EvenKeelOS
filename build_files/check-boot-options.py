#!/usr/bin/python3 -I
"""Build check for Boot options, run in the image after build.sh has installed them."""
import subprocess
import sys

sys.path.insert(0, "/usr/lib/evenkeel-os")
import evenkeel_os_bootopts as bootopts  # noqa: E402

problems = []
r = subprocess.run(["rpm-ostree", "kargs", "--help"], capture_output=True, text=True)
if r.returncode != 0 or not all(o in r.stdout for o in ("--append-if-missing", "--delete-if-present",
                                                        "--unchanged-exit-77")):
    problems.append("rpm-ostree kargs in this image can't add and take out settings the way Boot options needs")
for settings, title, _ in bootopts.COMMON:
    for s in settings:
        if bootopts.problem(s) or bootopts.risk(s):
            problems.append(f"the common fix {s} ({title}) is refused or warned about")
risky = ["selinux=0", "selinux=00", "selinux=0x0", "SELINUX=0", "enforcing=0", "lsm=landlock", "security=none",
         "lockdown=none", "module.sig_enforce=0", "module.sig-enforce=n", "mitigations=off", "mitigations=OFF",
         "nopti", "pti=off", "spectre_v2=off", "nospectre_v2", "nokaslr", "iommu=off", "intel_iommu=off",
         "amd_iommu=off", "audit=0", "sysrq_always_enabled", "rd.break", "rd.shell", "single", "emergency",
         "rescue", "rd.rescue", "rd.emergency", "3", "1", "S", "systemd.unit=rescue.target",
         "rd.systemd.unit=emergency.target", "systemd.mask=gdm.service", "systemd.debug_shell",
         "systemd.debug-shell=1", "rd.systemd.debug_shell", "nomodeset", "amdgpu.dc=0", "amdgpu.modeset=0",
         "i915.modeset=0", "xe.modeset=0", "acpi=off", "noapic", "nosmp", "mem=1G", "maxcpus=0", "efi=noruntime",
         "modprobe.blacklist=nvme", "module_blacklist=nvme", "rd.driver.blacklist=nvme", "systemd.debug_shell=tty9",
         "rd.shell=t", "spectre_v2_user=off", "spec_store_bypass_disable=off", "nospec_store_bypass_disable",
         "l1tf=off", "mds=off", "retbleed=off", "tsx=on", "nosmap", "nosmep", "kvm.nx_huge_pages=off", "memmap=2G@1G",
         "nolapic", "acpi=noirq", "noefi"]
for s in risky:
    if bootopts.problem(s) or not bootopts.risk(s):
        problems.append(f"{s} doesn't get a warning")
for s in ("selinux=1", "enforcing=1", "module.sig_enforce=1", "mitigations=auto,nosmt", "rd.shell=0",
          "systemd.debug_shell=0", "systemd.unit=graphical.target", "quiet", "acpi_osi=!", "video=eDP-1:1920x1080@60",
          "resume=UUID=1234-abcd", "5", "rd.shell=f"):
    if bootopts.problem(s) or bootopts.risk(s):
        problems.append(f"{s} is refused or warned about, but it's harmless")
refused = ["root=/dev/sda1", "rootflags=subvol=x", "ostree=/ostree/boot.0/x", "rw", "ro", "BOOT_IMAGE=x", "initrd=x",
           "rd.luks.uuid=x", "rd.luks.options=x", "luks=no", "rd.lvm.lv=x", "rd.md=0", "rd.auto", "fstab=0",
           "systemd.volatile=yes", "mount.usr=x", "composefs=0", "ostree.prepare-root.composefs=0",
           "evenkeel_os.test_rollback=quick", "init=/bin/sh", "rdinit=/bin/sh", "systemd.run=/x",
           "systemd.run_success_action=reboot", "--source=x", "-x", "a b", "a;id", "$(id)",
           "a=b c", 'acpi_osi="Windows 2020"', "é=1", "", "x" * 65, "a=" + "b" * 129, "a=b\nc", "=1"]
for s in refused:
    if not bootopts.problem(s):
        problems.append(f"{s!r} is accepted")
if bootopts.merged(["amdgpu.dcdebugmask=0x10", "quiet"], ["amdgpu.dcdebugmask=0x410", "quiet", "quiet"]) != \
        ["amdgpu.dcdebugmask=0x410", "quiet"]:
    problems.append("adding a setting doubles it, or keeps two values for one name")
if not bootopts.same(["quiet", "ostree=/ostree/boot.1/a/b/0", "rhgb"],
                     ["BOOT_IMAGE=(hd0,gpt2)/x", "rhgb", "quiet", "ostree=/ostree/boot.0/a/b/0"]):
    problems.append("the next start looks different from this one when only the boot menu's own entries differ")
if problems:
    print("ERROR: Boot options isn't set up right:\n  " + "\n  ".join(problems))
    sys.exit(1)
print(f"Boot options: {len(bootopts.COMMON)} common fixes allowed, {len(risky)} risky settings warned about, "
      f"{len(refused)} bad ones refused")
