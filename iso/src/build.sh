#!/usr/bin/bash
# Live USB image with the installer. Based on titanoboa's Bazzite example (Apache-2.0).
set -exo pipefail

IMAGE=ghcr.io/ctsdownloads/evenkeel-os:latest

# Directory that /root links to.
mkdir -p "$(realpath /root)"

# The live session

# No updates, setup, first-login questions or rollback checks in the live session.
for s in uupd.timer brew-setup.service podman-auto-update.timer tailscaled.service \
         evenkeel-os-codecs-setup.service evenkeel-os-disk-unlock-check.service rpm-ostreed-automatic.timer \
         evenkeel-os-flatpak-apps.service greenboot-healthcheck.service; do
  if systemctl cat "$s" >/dev/null 2>&1; then systemctl disable "$s"; else echo "note: $s is not in this image"; fi
done
rm -f /etc/xdg/autostart/evenkeel-os-setup-checklist.desktop /etc/xdg/autostart/evenkeel-os-packages-after-restart.desktop \
  /etc/xdg/autostart/evenkeel-os-rolled-back.desktop /etc/xdg/autostart/evenkeel-os-network-ask.desktop \
  /etc/xdg/autostart/evenkeel-os-guide.desktop

# The live user and its automatic login.
dnf install -y livesys-scripts
sed -i "s/^livesys_session=.*/livesys_session=gnome/" /etc/sysconfig/livesys
systemctl enable livesys.service livesys-late.service

# Welcome window: the fit check for this computer, then Install EvenKeelOS or Try it first.
install -Dm755 /src/evenkeel-os-live-welcome /usr/libexec/evenkeel-os-live-welcome
install -Dm644 /src/evenkeel-os-live-welcome.desktop /etc/xdg/autostart/evenkeel-os-live-welcome.desktop

# The installer

# The installer: screens as the live user, disk work as root through pkexec (live USB only).
dnf install -y python3-gobject gtk4 libadwaita python3-langtable python3-pwquality qrencode xkeyboard-config \
    dosfstools xfsprogs cryptsetup mdadm
install -d /usr/lib/evenkeel-os-installer
install -m755 /src/evenkeel-os-installer/evenkeel-os-installer /usr/lib/evenkeel-os-installer/
install -m644 /src/evenkeel-os-installer/*.py /src/evenkeel-os-installer/*.css /src/evenkeel-os-installer/*.png \
    /usr/lib/evenkeel-os-installer/
ln -sf ../lib/evenkeel-os-installer/evenkeel-os-installer /usr/bin/evenkeel-os-installer
install -Dm755 /src/evenkeel-os-install-engine /usr/libexec/evenkeel-os-install-engine
install -Dm644 /src/io.github.ctsdownloads.evenkeel-os.install.policy \
    /usr/share/polkit-1/actions/io.github.ctsdownloads.evenkeel-os.install.policy
install -Dm644 /src/io.github.ctsdownloads.EvenKeelOS.Installer.desktop \
    /usr/share/applications/io.github.ctsdownloads.EvenKeelOS.Installer.desktop
install -Dm644 /branding/logo-EvenKeel.svg /usr/share/icons/hicolor/scalable/apps/evenkeel-os-installer.svg
gtk-update-icon-cache -f /usr/share/icons/hicolor
install -Dm644 /build-branding/logo-EvenKeel-wide.svg /usr/share/evenkeel-os-installer/logo-wide.svg

# Dock: installer, Firefox, Files, Bazaar.
cat > /usr/share/glib-2.0/schemas/zz2-evenkeel-os-live.gschema.override <<'OVR'
[org.gnome.shell]
favorite-apps=['io.github.ctsdownloads.EvenKeelOS.Installer.desktop', 'org.mozilla.firefox.desktop', 'org.gnome.Nautilus.desktop', 'io.github.kolunmi.Bazaar.desktop']
welcome-dialog-last-shown-version='4294967295'

[org.gnome.desktop.session]
idle-delay=uint32 0

[org.gnome.settings-daemon.plugins.power]
ambient-enabled=false
idle-dim=false
power-saver-profile-on-low-battery=false
sleep-inactive-ac-type='nothing'
sleep-inactive-battery-type='nothing'
OVR

# No Flatpaks on the live USB: the Logo Menu opens gnome-system-monitor.
sed -i "s|^menu-button-system-monitor=.*|menu-button-system-monitor='gnome-system-monitor'|" \
  /etc/dconf/db/distro.d/50-evenkeel-os-logo-menu
grep -qx "menu-button-system-monitor='gnome-system-monitor'" /etc/dconf/db/distro.d/50-evenkeel-os-logo-menu \
  || { echo "ERROR: the live USB's Logo Menu system monitor was not set to gnome-system-monitor"; exit 1; }
dconf update
glib-compile-schemas /usr/share/glib-2.0/schemas

# Install from the copy on the USB; updates then come from the signed image on GitHub.
if [ -f /src/payload.oci.tar ]; then
  loaded=$(podman load -q -i /src/payload.oci.tar | sed -n 's/^Loaded image: //p' | tail -1)
  [ -n "$loaded" ] || { echo "ERROR: the local copy of EvenKeelOS could not be loaded"; exit 1; }
  podman tag "$loaded" "$IMAGE"
  [ "$loaded" = "$IMAGE" ] || podman untag "$IMAGE" "$loaded"
  echo "payload: the locally built image (test build)"
else
  podman pull "$IMAGE"
fi

# Live boot

dnf install -y dracut-live
kernel=$(kernel-install list --json pretty | jq -r '.[] | select(.has_kernel == true) | .version')
DRACUT_NO_XATTR=1 dracut -v --force --zstd --reproducible --no-hostonly \
    --add "dmsquash-live dmsquash-live-autooverlay" \
    "/usr/lib/modules/${kernel}/initramfs.img" "${kernel}"

# Fedora's signed shim and grub, as on Bazzite's USB, so it starts with Secure Boot on.
dnf install -y grub2-efi-x64-cdboot
mkdir -p /boot/efi
cp -av /usr/lib/efi/*/*/EFI /boot/efi/
# grub in place of shim's fallback, which would add a "Fedora" entry to the PC's boot list.
cp -v /boot/efi/EFI/fedora/grubx64.efi /boot/efi/EFI/BOOT/fbx64.efi

# Needed for image-builder's buildroot.
dnf install -y xorriso isomd5sum squashfs-tools

mkdir -p /usr/lib/bootc-image-builder
cp /src/iso.yaml /usr/lib/bootc-image-builder/iso.yaml

dnf clean all

# Checks: fail the build, never ship it wrong

fail() { echo "ERROR: $*"; exit 1; }
rpm -q anaconda-core >/dev/null 2>&1 && fail "Fedora's installer (Anaconda) is still on the USB"
for f in /usr/bin/evenkeel-os-installer /usr/libexec/evenkeel-os-install-engine; do
  [ -x "$f" ] || fail "$f is missing"
done
[ -s /usr/share/applications/io.github.ctsdownloads.EvenKeelOS.Installer.desktop ] || fail "the installer's launcher is missing"
[ -s /usr/share/polkit-1/actions/io.github.ctsdownloads.evenkeel-os.install.policy ] || fail "the installer's polkit action is missing"
[ -s /usr/share/evenkeel-os-installer/logo-wide.svg ] || fail "the installer's EvenKeelOS logo is missing"
# The file systems the install engine loads and mounts are in the USB's kernel.
for fs in xfs ext4 vfat; do
  modinfo -k "$kernel" "$fs" >/dev/null 2>&1 || fail "kernel $kernel has no $fs, which the installer needs"
done
for k in current windows; do
  [ -s "/usr/lib/evenkeel-os-installer/layout-$k.png" ] || fail "the installer's $k layout picture is missing"
done
# The extensions the installer turns on for the Windows layout are installed.
windows=$(python3 -I -c 'import runpy; print(*runpy.run_path("/usr/libexec/evenkeel-os-install-engine")["layout_extensions"]("", "windows"))')
[ -n "$windows" ] || fail "the installer finds no extensions for the Windows layout"
for x in $windows; do
  [ -s "/usr/share/gnome-shell/extensions/$x/metadata.json" ] || fail "the installer's Windows layout needs $x, which is not installed"
done
# "I already use Linux" writes the file that keeps New to EvenKeelOS? closed at login, where Wheelhouse looks for it.
linux_choice="the installer's Linux choice wouldn't stop New to EvenKeelOS? at login"
env -u XDG_STATE_HOME HOME=/h python3 -I - <<'PY' || fail "$linux_choice"
import runpy, sys
sys.path.insert(0, "/usr/lib/evenkeel-os")
from evenkeel_os_ui import load_program
tools = load_program("/usr/bin/evenkeel-os-tools", "tools")
engine = runpy.run_path("/usr/libexec/evenkeel-os-install-engine")["GUIDE_HIDDEN"]
sys.exit(str(tools.GUIDE_HIDDEN) != "/h/" + engine)
PY
# The installer lists only languages EvenKeelOS is translated into (from the image's evenkeel-os.mo files).
mo=(/usr/share/locale/*/LC_MESSAGES/evenkeel-os.mo)
[ -f "${mo[0]}" ] && [ "${#mo[@]}" -ge 66 ] || fail "EvenKeelOS's translations are missing"
[ -f /usr/share/locale/de/LC_MESSAGES/xkeyboard-config.mo ] || fail "keyboard names have no translations"
# The fit check runs, and knows the kernel's message for a disk hidden by the BIOS's RAID setting.
python3 -I - <<'PY' || fail "the live USB's fit check doesn't work"
import sys
sys.path.insert(0, "/usr/lib/evenkeel-os-installer")
import fitcheck
results = fitcheck.check()
assert results and all(r[0] in (fitcheck.GOOD, fitcheck.LIMITED, fitcheck.BAD) for r in results)
assert fitcheck.raid_hidden("ahci 0000:00:17.0: Found 1 remapped NVMe devices.")
assert not fitcheck.raid_hidden("ahci 0000:00:17.0: AHCI 0001.0301 32 slots")
fitcheck.report(results)
# NVIDIA with its open-source driver is fine; any graphics chip with no driver is a problem.
card = lambda vendor, driver: {"class": "0x030000", "vendor": vendor, "driver": driver, "slot": "0000:01:00.0"}
fitcheck.read = lambda path: ""
assert fitcheck.graphics([card("0x10de", "nouveau")])[0] == fitcheck.GOOD
assert "AMD graphics drive the screen" in fitcheck.graphics([card("0x1002", "amdgpu"), card("0x10de", "nouveau")])[3]
assert fitcheck.graphics([card("0x10de", "")])[0] == fitcheck.BAD
PY
python3 -I -c 'import ast, sys; ast.parse(open(sys.argv[1]).read())' /usr/libexec/evenkeel-os-live-welcome \
  || fail "the live welcome window has a syntax error"
for icon in object-select-symbolic dialog-warning-symbolic dialog-error-symbolic; do
  found=$(find /usr/share/icons/Adwaita -name "$icon.svg" -print -quit)
  [ -n "$found" ] || fail "the fit check's $icon icon is missing"
done
command -v qrencode >/dev/null || fail "qrencode is missing (the problem report's QR code)"
for tool in mdadm dmsetup cryptsetup mkfs.fat mkfs.ext4 mkfs.xfs sfdisk wipefs hwclock; do
  command -v "$tool" >/dev/null || fail "$tool is missing (the install engine uses it)"
done
# Live session never dims, locks or suspends (read through the schemas).
for setting in "org.gnome.desktop.session idle-delay uint32 0" \
               "org.gnome.settings-daemon.plugins.power ambient-enabled false" \
               "org.gnome.settings-daemon.plugins.power idle-dim false" \
               "org.gnome.settings-daemon.plugins.power power-saver-profile-on-low-battery false" \
               "org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'" \
               "org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'"; do
  set -- $setting
  schema=$1 key=$2
  shift 2
  [ "$(gsettings get "$schema" "$key")" = "$*" ] || fail "the live session's $key is not $*, so an install nobody touches could be interrupted"
done
# Live Logo Menu opens gnome-system-monitor.
[ "$(HOME=/tmp gsettings get org.gnome.shell.extensions.logo-menu menu-button-system-monitor)" = "'gnome-system-monitor'" ] \
  || fail "the live USB's Logo Menu system monitor is not gnome-system-monitor"
# bootc steps: copy, write settings, then finish.
bootc install to-filesystem --help | grep -q -- '--skip-finalize' || fail "bootc has no install to-filesystem --skip-finalize"
bootc install to-filesystem --help | grep -q -- '--bootloader' || fail "bootc has no install to-filesystem --bootloader"
bootc install finalize --help >/dev/null 2>&1 || fail "bootc has no install finalize"
# Every language offered must work on the installed system.
rpm -q glibc-all-langpacks >/dev/null || fail "glibc-all-langpacks is missing: the languages offered would not work"
# The installer window starts, and its language, keyboard and time zone lists load.
python3 -I -c '
import sys; sys.path.insert(0, "/usr/lib/evenkeel-os-installer")
import gi; gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk
import data, pwquality
import i18n, langtable
translated = {langtable.parse_locale(t).language for t in i18n.translations()} | {"en"}
assert {lang for lang, *_ in data.languages()} == translated, "languages"
assert len(data.keyboards()) >= 500, "keyboards"
# kbd-misc ships with the image, so the installed system has these keymaps.
assert data.has_console_keymap("us") and data.has_console_keymap("de(nodeadkeys)"), "keyboards for the disk password"
assert len(data.timezones()) >= 9, "time zones"
' || fail "the installer's lists could not be read"
grep -qi 'fedora' /etc/system-release && fail "/etc/system-release still says Fedora"
podman image exists "$IMAGE" || fail "the copy of EvenKeelOS for the installer is missing"
# The install writes greenboot's counter into the boot menu; without it, installs get no automatic rollback.
grep -q boot_counter /usr/lib/bootupd/grub2-static/configs.d/08_greenboot.cfg || fail "this EvenKeelOS has no automatic rollback counter for the boot menu"
# Secure Boot: the USB starts Fedora's shim and grub, exactly as Fedora ships them.
efi=/boot/efi/EFI
cmp -s "$efi/BOOT/BOOTX64.EFI" "$(rpm -ql shim-x64 | grep '^/usr/lib/efi/.*/EFI/fedora/shimx64.efi$')" || fail "the USB does not start from Fedora's shim"
cmp -s "$efi/fedora/grubx64.efi" "$(rpm -ql grub2-efi-x64 | grep '^/usr/lib/efi/.*/EFI/fedora/grubx64.efi$')" || fail "the USB's grub is not Fedora's"
cmp -s "$efi/BOOT/fbx64.efi" "$efi/fedora/grubx64.efi" || fail "shim's fallback would add a boot entry to the PC"
cmp -s "$efi/fedora/BOOTX64.CSV" "$(rpm -ql shim-x64 | grep '^/usr/lib/efi/.*/EFI/fedora/BOOTX64.CSV$')" || fail "shim's BOOTX64.CSV was changed"
grep -aq 'Microsoft Corporation UEFI CA' "$efi/BOOT/BOOTX64.EFI" || fail "the USB's shim is not signed for Secure Boot"
grep -aq 'Fedora Secure Boot' "$efi/fedora/grubx64.efi" || fail "the USB's grub is not signed by Fedora"
# Big layers fill the live session's memory during install, so the image must be split into small ones.
[ "$(podman image inspect "$IMAGE" --format '{{len .RootFS.Layers}}')" -ge 20 ] || fail "the copy of EvenKeelOS for the installer is not split into small layers"
echo "live image ready: installer in place, payload $IMAGE present"
