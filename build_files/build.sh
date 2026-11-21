#!/bin/bash
set -ouex pipefail

NAME=evenkeel-os

dnf5 -y install firefox v4l-utils xdg-terminal-exec
xargs -a /ctx/bluefin-packages.txt dnf5 -y install
# Default apps from Fedora (default-apps.txt); fails if any is missing.
grep -v '^#' /ctx/default-apps.txt | xargs dnf5 -y install
# Ghostty (scottames/ghostty COPR) replaces Ptyxis as the default terminal.
curl -fsSL --retry 3 "https://copr.fedorainfracloud.org/coprs/scottames/ghostty/repo/fedora-$(rpm -E %fedora)/scottames-ghostty-fedora-$(rpm -E %fedora).repo" -o /etc/yum.repos.d/ghostty.repo
dnf5 -y install ghostty
rm -f /etc/yum.repos.d/ghostty.repo
dnf5 -y remove ptyxis
rpm -q ptyxis >/dev/null 2>&1 && { echo "ERROR: Ptyxis is still installed"; exit 1; }
install -Dm644 /ctx/xdg-terminals.list /etc/xdg/xdg-terminals.list
[ -s /usr/share/applications/com.mitchellh.ghostty.desktop ] || { echo "ERROR: Ghostty's launcher is missing, so xdg-terminal-exec has no terminal"; exit 1; }
for p in $(grep -v '^#' /ctx/default-apps.txt) firefox nautilus ghostty nautilus-python gnome-control-center orca; do
  rpm -q "$p" >/dev/null || { echo "ERROR: default app $p is not installed"; exit 1; }
done
# uupd, Homebrew and Bazaar from Universal Blue; Bazaar replaces GNOME Software.
curl -fsSL --retry 3 "https://copr.fedorainfracloud.org/coprs/ublue-os/packages/repo/fedora-$(rpm -E %fedora)/ublue-os-packages-fedora-$(rpm -E %fedora).repo" -o /etc/yum.repos.d/ublue-os-packages.repo
dnf5 -y install uupd ublue-brew ublue-os-just bazaar
rm -f /etc/yum.repos.d/ublue-os-packages.repo
dnf5 -y remove gnome-software gnome-software-rpm-ostree
# No GNOME tour: its Welcome popup would cover the setup checklist.
dnf5 -y remove gnome-tour
for p in gnome-software gnome-software-rpm-ostree; do rpm -q "$p" >/dev/null 2>&1 && { echo "ERROR: $p is still installed"; exit 1; }; done
rpm -q bazaar >/dev/null || { echo "ERROR: Bazaar is not installed"; exit 1; }
[ -f /usr/share/gnome-shell/search-providers/io.github.kolunmi.Bazaar.search-provider.ini ] && [ -f /usr/share/dbus-1/services/io.github.kolunmi.Bazaar.SearchProvider.service ] || { echo "ERROR: Bazaar's Super-search provider is missing"; exit 1; }
command -v ujust >/dev/null || { echo 'ERROR: ujust is missing'; exit 1; }
# Shared windows module for System Tools and Install Package File.
install -Dm644 /ctx/evenkeel_os_ui.py /usr/lib/evenkeel-os/evenkeel_os_ui.py
python3 -I -c 'import sys; sys.path.insert(0, "/usr/lib/evenkeel-os"); import evenkeel_os_ui' \
  || { echo "ERROR: the shared windows module does not load"; exit 1; }
# System Update: uupd with a progress window, no password (uupd's polkit rule, narrowed to the person at the computer).
install -Dm644 /ctx/40-evenkeel-os-uupd.rules /usr/share/polkit-1/rules.d/40-evenkeel-os-uupd.rules
install -Dm755 /ctx/evenkeel-os-update /usr/bin/evenkeel-os-update
install -Dm755 /ctx/evenkeel-os-update-helper /usr/libexec/evenkeel-os-update-helper
echo '{"deployments": [{"staged": true}]}' | /usr/libexec/evenkeel-os-update-helper staged \
  || { echo "ERROR: the System Update helper does not run"; exit 1; }
install -Dm644 /ctx/evenkeel-os-update.desktop /usr/share/applications/evenkeel-os-update.desktop
# Install Package File: .rpm and .deb apps go into Fedora and Ubuntu boxes.
install -Dm755 /ctx/evenkeel-os-packages /usr/bin/evenkeel-os-packages
install -d /usr/lib/evenkeel-os/evenkeel_os_packages
install -m644 /ctx/evenkeel_os_packages/*.py /usr/lib/evenkeel-os/evenkeel_os_packages/
python3 -I -c 'import sys, pkgutil, importlib; sys.path.insert(0, "/usr/lib/evenkeel-os"); import evenkeel_os_packages as p
[importlib.import_module("evenkeel_os_packages." + m.name) for m in pkgutil.iter_modules(p.__path__)]' \
  || { echo "ERROR: Install Package File's parts do not load"; exit 1; }
install -Dm755 /ctx/evenkeel-os-hwrules /usr/libexec/evenkeel-os-hwrules
# Starts box apps from Show Apps and stops them on Quit.
install -Dm755 /ctx/evenkeel-os-box-run /usr/libexec/evenkeel-os-box-run
install -Dm644 /ctx/io.github.ctsdownloads.evenkeel-os.hwrules.policy /usr/share/polkit-1/actions/io.github.ctsdownloads.evenkeel-os.hwrules.policy
# System Tools, with a root helper for the jobs that change the system.
install -Dm755 /ctx/evenkeel-os-tools /usr/bin/evenkeel-os-tools
install -Dm755 /ctx/evenkeel-os-tools-admin /usr/libexec/evenkeel-os-tools-admin
install -Dm644 /ctx/io.github.ctsdownloads.evenkeel-os.tools.policy /usr/share/polkit-1/actions/io.github.ctsdownloads.evenkeel-os.tools.policy
# Harmless System Tools jobs need no password for an admin at the computer.
install -Dm755 /ctx/evenkeel-os-tools-safe /usr/libexec/evenkeel-os-tools-safe
# Automatic updates pause for 3 days after an undo; System Update itself is never paused.
install -Dm755 /ctx/evenkeel-os-updates-pause-check /usr/libexec/evenkeel-os-updates-pause-check
install -Dm644 /ctx/50-evenkeel-os-pause.conf /usr/lib/systemd/system/uupd.service.d/50-evenkeel-os-pause.conf
grep -qx 'ExecCondition=/usr/libexec/evenkeel-os-updates-pause-check' /usr/lib/systemd/system/uupd.service.d/50-evenkeel-os-pause.conf || { echo "ERROR: automatic updates do not check for a pause"; exit 1; }
[ ! -e /usr/lib/systemd/system/uupd-manual.service.d ] || { echo "ERROR: System Update's own run has a drop-in; check it is not paused"; exit 1; }
pause=/var/lib/evenkeel-os/updates-paused-until
mkdir -p "${pause%/*}"
echo $(( $(date +%s) + 3600 )) > "$pause"
! /usr/libexec/evenkeel-os-updates-pause-check || { echo "ERROR: a pause does not stop automatic updates"; exit 1; }
echo $(( $(date +%s) - 1 )) > "$pause"
/usr/libexec/evenkeel-os-updates-pause-check && [ ! -e "$pause" ] || { echo "ERROR: an ended pause is not cleared"; exit 1; }
rmdir --ignore-fail-on-non-empty "${pause%/*}"
install -Dm644 /ctx/50-evenkeel-os-tools.rules /usr/share/polkit-1/rules.d/50-evenkeel-os-tools.rules
python3 -c 'import xml.dom.minidom,sys; [xml.dom.minidom.parse(f) for f in sys.argv[1:]]' \
  /ctx/io.github.ctsdownloads.evenkeel-os.tools.policy /ctx/io.github.ctsdownloads.evenkeel-os.codecs.policy \
  || { echo "ERROR: a System Tools or codecs polkit policy is not valid XML"; exit 1; }
# Keep the disk unlock note in step with the disk at every start.
install -Dm644 /ctx/evenkeel-os-disk-unlock-check.service /usr/lib/systemd/system/evenkeel-os-disk-unlock-check.service
systemctl enable evenkeel-os-disk-unlock-check.service
install -Dm644 /ctx/evenkeel-os-tools.desktop /usr/share/applications/evenkeel-os-tools.desktop
# The setup checklist opens once at a new user's first login.
install -Dm644 /ctx/evenkeel-os-setup-checklist.desktop /etc/xdg/autostart/evenkeel-os-setup-checklist.desktop
install -Dm644 /ctx/evenkeel-os-rolled-back.desktop /etc/xdg/autostart/evenkeel-os-rolled-back.desktop
rm -f /etc/xdg/autostart/evenkeel-os-codecs-prompt.desktop
# Change list for System Update (empty in local builds).
install -Dm644 /dev/null /usr/share/evenkeel-os/changes.txt
[ -f /ctx/changes.txt ] && install -Dm644 /ctx/changes.txt /usr/share/evenkeel-os/changes.txt
# Microphones start at 50%; fail if WirePlumber drops the setting.
install -Dm644 /ctx/60-evenkeel-os-mic.conf /usr/share/wireplumber/wireplumber.conf.d/60-evenkeel-os-mic.conf
grep -q 'device.routes.default-source-volume' /usr/share/wireplumber/wireplumber.conf || { echo "ERROR: WirePlumber no longer has device.routes.default-source-volume"; exit 1; }
for c in fwupdmgr systemd-cryptenroll cryptsetup flatpak podman gnome-control-center; do command -v "$c" >/dev/null || { echo "ERROR: System Tools needs $c"; exit 1; }; done
install -Dm644 /ctx/evenkeel-os-install-package.desktop /usr/share/applications/evenkeel-os-install-package.desktop
install -Dm644 /ctx/evenkeel-os-windows-program.desktop /usr/share/applications/evenkeel-os-windows-program.desktop
install -Dm644 /ctx/evenkeel-os-remove-apps.desktop /usr/share/applications/evenkeel-os-remove-apps.desktop
install -Dm644 /ctx/evenkeel-os-repair-boxes.desktop /usr/share/applications/evenkeel-os-repair-boxes.desktop
install -Dm644 /ctx/evenkeel-os-login-apps.desktop /usr/share/applications/evenkeel-os-login-apps.desktop
# At login, once: say when a package added to the system is ready.
install -Dm644 /ctx/evenkeel-os-packages-after-restart.desktop /etc/xdg/autostart/evenkeel-os-packages-after-restart.desktop
# GNOME never runs autostart entries that name a startup phase; fail if ours do.
if grep -l '^X-GNOME-Autostart-Phase=' /etc/xdg/autostart/evenkeel-os-*.desktop 2>/dev/null; then
  echo "ERROR: the autostart entries above name a GNOME startup phase, so they would never run at login"; exit 1
fi
# Our default apps go in /etc/xdg; Fedora's gnome-mimeapps.list stays as is.
install -Dm644 /ctx/gnome-mimeapps.list /etc/xdg/gnome-mimeapps.list
grep -q '^text/plain=org.gnome.TextEditor.desktop$' /usr/share/applications/gnome-mimeapps.list || { echo "ERROR: Fedora's GNOME default apps file is missing or changed"; exit 1; }
update-desktop-database /usr/share/applications
for t in application/x-rpm application/vnd.debian.binary-package; do
  first=$(XDG_CURRENT_DESKTOP=GNOME gio mime "$t" | sed -n 1p)
  [[ "$first" == *evenkeel-os-install-package.desktop* ]] || { echo "ERROR: $t files do not open in Install Package File"; exit 1; }
done
for t in application/vnd.microsoft.portable-executable application/x-msi; do
  first=$(XDG_CURRENT_DESKTOP=GNOME gio mime "$t" | sed -n 1p)
  [[ "$first" == *evenkeel-os-windows-program.desktop* ]] || { echo "ERROR: $t files do not open in Windows Program"; exit 1; }
done
for c in distrobox podman flatpak rpm2archive pkexec zenity dnf5; do command -v "$c" >/dev/null || { echo "ERROR: Install Package File needs $c"; exit 1; }; done
mkdir -p /tmp/pkgtest && (cd /tmp/pkgtest && dnf5 -q download gnome-mines openvpn solaar-udev fedora-repos-archive)
python3 -I /ctx/check-packages.py /tmp/pkgtest || { echo 'ERROR: Install Package File does not read packages correctly'; exit 1; }
rm -rf /tmp/pkgtest
# Windows Program: an .exe or .msi offers its Linux version from Flathub, from a list made fresh each build
# out of winget's program index (Microsoft) and the app lists of Flathub, Fedora and Ubuntu.
dnf5 -y install msitools python3-pefile
mkdir -p /tmp/winlist /usr/share/evenkeel-os
curl -fsSL --retry 3 https://cdn.winget.microsoft.com/cache/source.msix -o /tmp/winlist/source.msix
python3 -I -m zipfile -e /tmp/winlist/source.msix /tmp/winlist/msix
curl -fsSL --retry 3 https://dl.flathub.org/repo/appstream/x86_64/appstream.xml.gz -o /tmp/winlist/flathub.xml.gz
# Ubuntu's lists are for the Ubuntu box's version (24.04); Fedora's is the image's own.
for c in main universe; do
  curl -fsSL --retry 3 -o "/tmp/winlist/ubuntu-$c.yml.gz" \
    "https://archive.ubuntu.com/ubuntu/dists/noble/$c/dep11/Components-amd64.yml.gz"
done
python3 -I /ctx/make-windows-list.py /tmp/winlist/msix/Public/index.db /tmp/winlist/flathub.xml.gz \
  /usr/share/swcatalog/xml/fedora.xml.gz /tmp/winlist/ubuntu-main.yml.gz /tmp/winlist/ubuntu-universe.yml.gz \
  /usr/share/evenkeel-os/windows-apps.json
# Five real installers, pinned by checksum, to test reading .exe and .msi files.
(cd /tmp/winlist && curl -fsSL --retry 3 -O https://www.7-zip.org/a/7z2606-x64.exe \
  -O https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.9.9.1/npp.8.9.9.1.Installer.x64.exe \
  -O https://the.earth.li/~sgtatham/putty/0.85/w64/putty-64bit-0.85-installer.msi \
  -O https://github.com/bitwarden/clients/releases/download/desktop-v2026.11.0/bit-Bitwarden-Installer-2026.11.0.exe \
  -O https://github.com/qutebrowser/qutebrowser/releases/download/v3.7.0/qutebrowser-3.7.0-amd64.exe)
(cd /tmp/winlist && sha256sum -c --quiet) <<'SUMS' || { echo "ERROR: a test installer for Windows Program has changed"; exit 1; }
9b697f65ecc2d9b0152f5ee96d72dde522a7827690349d9307935dacf40f42ec  7z2606-x64.exe
ce3267f5c4e7e42f847e00f4b20234da6150647203033cdde34a69593efc3152  npp.8.9.9.1.Installer.x64.exe
2213ebacf962b709411d654a40087508a694756bc4e41c5a1c24ad86596b2511  putty-64bit-0.85-installer.msi
c8e7ee33b43b9fd6baada11b4355a684bb8944ea58173423fa108d244bcbdf0a  bit-Bitwarden-Installer-2026.11.0.exe
8956c0614fcea863730559109e9787ccce37034d72a7faf954945361e58ec48d  qutebrowser-3.7.0-amd64.exe
SUMS
python3 -I /ctx/check-windows-programs.py /tmp/winlist || { echo 'ERROR: Windows Program does not read installers correctly'; exit 1; }
rm -rf /tmp/winlist
# Services on by default, including after the first boot.
printf 'enable brew-setup.service\nenable evenkeel-os-codecs-setup.service\nenable evenkeel-os-flathub.service\nenable evenkeel-os-flatpak-apps.service\ndisable flatpak-add-fedora-repos.service\nenable evenkeel-os-disk-unlock-check.service\nenable tailscaled.service\nenable podman-auto-update.timer\nenable uupd.timer\nenable greenboot-healthcheck.service\nenable greenboot-set-rollback-trigger.service\n' > /usr/lib/systemd/system-preset/80-evenkeel-os.preset
systemctl enable tailscaled.service podman-auto-update.timer uupd.timer brew-setup.service
for u in tailscaled.service uupd.timer brew-setup.service; do [ "$(systemctl is-enabled "$u")" = enabled ] || { echo "ERROR: $u is not enabled"; exit 1; }; done
bash /ctx/rebrand.sh
# Automatic rollback: greenboot with our own checks. Fedora's default checks fail offline, so they stay out.
dnf5 -y install greenboot
# 2 bad starts in a row, then back to the previous version (greenboot's default is 4).
sed -i 's/^GREENBOOT_MAX_BOOT_ATTEMPTS=.*/GREENBOOT_MAX_BOOT_ATTEMPTS=1/' /etc/greenboot/greenboot.conf
grep -qx 'GREENBOOT_MAX_BOOT_ATTEMPTS=1' /etc/greenboot/greenboot.conf || { echo "ERROR: greenboot's retry count isn't 1"; exit 1; }
# greenboot's boot menu file has no final line break, and bootupd joins the files without one, so its last command
# ran into the next line and the counter never counted; give it the line break.
gbcfg=/usr/lib/bootupd/grub2-static/configs.d/08_greenboot.cfg
[ -z "$(tail -c1 "$gbcfg")" ] || echo >>"$gbcfg"
# Build the boot menu the way bootupd does at install, and check it.
menu=$(mktemp)
{ cat /usr/lib/bootupd/grub2-static/grub-static-pre.cfg
  for f in /usr/lib/bootupd/grub2-static/configs.d/*.cfg; do
    printf '\n### BEGIN %s ###\n' "${f##*/}"; cat "$f"; printf '### END %s ###\n' "${f##*/}"
  done; } >"$menu"
grep -q '[^[:space:]]### END' "$menu" && { echo "ERROR: a boot menu file runs into the next one"; exit 1; }
grep -qx 'save_env boot_success' "$menu" || { echo "ERROR: the boot menu doesn't save boot_success"; exit 1; }
grub2-script-check "$menu" || { echo "ERROR: the boot menu bootupd would write fails GRUB's syntax check"; exit 1; }
rm -f "$menu"
! rpm -q greenboot-default-health-checks >/dev/null || { echo "ERROR: Fedora's default greenboot checks are installed; they fail offline"; exit 1; }
install -Dm755 -t /usr/lib/greenboot/check/required.d /ctx/greenboot/00-evenkeel-os-test-quick.sh \
  /ctx/greenboot/10-evenkeel-os-login-screen.sh /ctx/greenboot/20-evenkeel-os-networking.sh \
  /ctx/greenboot/30-evenkeel-os-desktop.sh
install -Dm755 -t /usr/lib/greenboot/green.d /ctx/greenboot/90-evenkeel-os-rolled-back.sh
install -Dm644 /ctx/greenboot/50-evenkeel-os-greenboot.conf /usr/lib/systemd/system/greenboot-healthcheck.service.d/50-evenkeel-os.conf
install -Dm755 /ctx/greenboot/evenkeel-os-greenboot-arm /usr/libexec/evenkeel-os-greenboot-arm
# Boot menus written before the fix above get the line break once, at the next start.
install -Dm755 /ctx/greenboot/evenkeel-os-boot-menu-repair /usr/libexec/evenkeel-os-boot-menu-repair
install -Dm644 /ctx/greenboot/evenkeel-os-boot-menu-repair.service /usr/lib/systemd/system/evenkeel-os-boot-menu-repair.service
systemctl enable evenkeel-os-boot-menu-repair.service
install -Dm644 /ctx/greenboot/50-evenkeel-os-arm.conf /usr/lib/systemd/system/greenboot-set-rollback-trigger.service.d/50-evenkeel-os.conf
# The arming step must run after greenboot's own (it reads greenboot's trial marker).
[ "$(systemctl cat greenboot-set-rollback-trigger.service | sed -n 's/^ExecStop=\([^ ]*\).*/\1/p' | tr '\n' ' ')" \
  = "/usr/libexec/greenboot/greenboot /usr/libexec/evenkeel-os-greenboot-arm " ] \
  || { echo "ERROR: greenboot-set-rollback-trigger's stop steps aren't greenboot then evenkeel-os-greenboot-arm"; exit 1; }
# Test automatic rollback: each test copy breaks one real thing, switched on by its kernel argument only.
install -Dm755 /ctx/greenboot/evenkeel-os-test-fail /usr/libexec/evenkeel-os-test-fail
install -Dm644 /ctx/greenboot/50-evenkeel-os-test-gdm.conf /usr/lib/systemd/system/gdm.service.d/50-evenkeel-os-test.conf
install -Dm644 /ctx/greenboot/50-evenkeel-os-test-networkmanager.conf \
  /usr/lib/systemd/system/NetworkManager.service.d/50-evenkeel-os-test.conf
install -Dm644 /ctx/greenboot/50-evenkeel-os-test-shell.conf /usr/lib/systemd/user/org.gnome.Shell@user.service.d/50-evenkeel-os-test.conf
install -Dm644 -t /usr/lib/systemd/system /ctx/greenboot/evenkeel-os-test-stuck.service /ctx/greenboot/evenkeel-os-test-freeze.service
systemctl enable evenkeel-os-test-stuck.service evenkeel-os-test-freeze.service
for u in gdm.service NetworkManager.service evenkeel-os-test-stuck.service evenkeel-os-test-freeze.service greenboot-healthcheck.service; do
  systemd-analyze verify "$u" 2>&1 | grep -iE "evenkeel|greenboot" && { echo "ERROR: $u has a unit problem"; exit 1; }
done
# The login-loop test needs the user desktop's own shell unit (the login screen uses org.gnome.Shell@gdm).
grep -qx 'Requires=org.gnome.Shell@user.service' /usr/lib/systemd/user/gnome-session@gnome.target.d/gnome.session.conf \
  || { echo "ERROR: GNOME's desktop no longer starts org.gnome.Shell@user.service; update the login-loop test"; exit 1; }
# Normal starts never trip a test: with no test kernel argument every test step passes.
python3 -I /ctx/check-rollback-tests.py
for f in /usr/lib/greenboot/check/required.d/*-evenkeel-os-*.sh /usr/lib/greenboot/green.d/*-evenkeel-os-*.sh \
         /usr/libexec/evenkeel-os-test-fail /usr/libexec/evenkeel-os-greenboot-arm /usr/libexec/evenkeel-os-boot-menu-repair; do
  bash -n "$f" || { echo "ERROR: $f has a syntax error"; exit 1; }
done
systemctl enable greenboot-healthcheck.service
for u in greenboot-healthcheck.service greenboot-set-rollback-trigger.service; do
  [ "$(systemctl is-enabled "$u")" = enabled ] || { echo "ERROR: $u is not enabled"; exit 1; }
done
# bootupd copies this into the boot menu at install; without it nothing counts failed starts.
grep -q boot_counter /usr/lib/bootupd/grub2-static/configs.d/08_greenboot.cfg || { echo "ERROR: greenboot's boot menu counter is missing"; exit 1; }
# The rollback note looks for these lines in greenboot's log.
for t in 'Rollback successful' 'Rollback to previous deployment completed' 'deployment has been rolled back'; do
  grep -aqF "$t" /usr/libexec/greenboot/greenboot || { echo "ERROR: greenboot no longer logs \"$t\"; update 90-evenkeel-os-rolled-back.sh"; exit 1; }
done
# TPM support in the boot image, for automatic disk unlock.
dnf5 -y install tpm2-tss
printf 'add_dracutmodules+=" tpm2-tss "\n' > /usr/lib/dracut/dracut.conf.d/90-evenkeel-os-tpm.conf
bash /ctx/initramfs.sh
install -Dm755 /ctx/evenkeel-os-boot-label /usr/bin/evenkeel-os-boot-label
install -Dm644 /ctx/NOTICE /usr/share/doc/evenkeel-os/NOTICE

# Fingerprint login on (Silverblue ships it off).
authselect enable-feature with-fingerprint
mkdir -p /usr/lib/systemd/system/fprintd.service.d
printf '[Install]\nWantedBy=graphical.target\n' > /usr/lib/systemd/system/fprintd.service.d/10-evenkeel-os-enable.conf
systemctl enable fprintd.service
dnf5 -y remove fedora-flathub-remote || echo "note: fedora-flathub-remote was not removed"
install -Dm644 /ctx/flathub.flatpakrepo /usr/share/evenkeel-os/flathub.flatpakrepo
install -Dm644 /ctx/evenkeel-os-flathub.service /usr/lib/systemd/system/evenkeel-os-flathub.service
# Default apps from Flathub, installed on the first start with internet.
install -Dm644 /ctx/flathub-apps.txt /usr/share/evenkeel-os/flathub-apps.txt
# Resources, the Logo Menu's system monitor, is one of them.
grep -qx net.nokyan.Resources /usr/share/evenkeel-os/flathub-apps.txt || { echo "ERROR: Resources (net.nokyan.Resources) is not in the Flathub apps list, so the Logo Menu's system monitor would be missing"; exit 1; }
install -Dm755 /ctx/evenkeel-os-flathub-apps /usr/libexec/evenkeel-os-flathub-apps
systemctl disable flatpak-add-fedora-repos.service
install -Dm644 /ctx/evenkeel-os-flatpak-apps.service /usr/lib/systemd/system/evenkeel-os-flatpak-apps.service
install -Dm755 /ctx/evenkeel-os-codecs /usr/bin/evenkeel-os-codecs
ln -sf evenkeel-os-codecs /usr/bin/codecs
ln -sf evenkeel-os-codecs /usr/bin/install-codecs
install -Dm644 /ctx/evenkeel-os-codecs.desktop /usr/share/applications/evenkeel-os-codecs.desktop
install -Dm644 /ctx/evenkeel-os-codecs-lib.sh /usr/libexec/evenkeel-os-codecs-lib.sh
install -Dm755 /ctx/evenkeel-os-codecs-setup /usr/libexec/evenkeel-os-codecs-setup
install -Dm755 /ctx/evenkeel-os-codecs-admin /usr/libexec/evenkeel-os-codecs-admin
install -Dm644 /ctx/io.github.ctsdownloads.evenkeel-os.codecs.policy /usr/share/polkit-1/actions/io.github.ctsdownloads.evenkeel-os.codecs.policy
install -Dm644 /ctx/50-evenkeel-os-codecs.rules /usr/share/polkit-1/rules.d/50-evenkeel-os-codecs.rules
# RPM Fusion for full codecs, copied in only when chosen; fail without its key.
install -Dm644 /ctx/rpmfusion-free.repo /usr/share/evenkeel-os/rpmfusion-free.repo
install -Dm644 /ctx/rpmfusion-free-updates.repo /usr/share/evenkeel-os/rpmfusion-free-updates.repo
[ -s "/usr/share/distribution-gpg-keys/rpmfusion/RPM-GPG-KEY-rpmfusion-free-fedora-$(rpm -E %fedora)" ] || { echo 'ERROR: the RPM Fusion signing key is missing'; exit 1; }
# Test-run both codec swaps so a new Fedora can't ship them broken.
( . /ctx/evenkeel-os-codecs-lib.sh   # subshell: keeps its PATH and umask to itself
  keys_before=$(rpm -qa gpg-pubkey --qf '%{VERSION}\n')
  cp /usr/share/evenkeel-os/rpmfusion-free.repo /usr/share/evenkeel-os/rpmfusion-free-updates.repo /etc/yum.repos.d/
  swap_ok=1
  dnf5 -y --setopt=tsflags=test --setopt=clean_requirements_on_remove=0 do \
    --action=remove $(present $FREE) \
    --action=install --from-repo=rpmfusion-free,rpmfusion-free-updates $FULL || swap_ok=0
  rm -f /etc/yum.repos.d/rpmfusion-free.repo /etc/yum.repos.d/rpmfusion-free-updates.repo
  # Same test for Web video only.
  web_ok=1
  rpm -q $STAND_IN >/dev/null && dnf5 -y --setopt=tsflags=test do --action=remove $STAND_IN --action=install $WEB \
    || web_ok=0
  for k in $(rpm -qa gpg-pubkey --qf '%{VERSION}\n'); do
    grep -qx "$k" <<<"$keys_before" || rpmkeys --delete "$k"
  done
  [ "$swap_ok" = 1 ] || { echo "ERROR: RPM Fusion's codecs do not install on Fedora $(rpm -E %fedora) yet, so \"Everything\" would fail for users. Wait for RPM Fusion, then rebuild."; exit 1; }
  [ "$web_ok" = 1 ] || { echo "ERROR: Cisco's OpenH264 does not install in place of $STAND_IN, so \"Web video only\" would fail for users"; exit 1; } )
# Kept so old negativo17 codec setups can still update.
install -Dm644 /ctx/RPM-GPG-KEY-negativo17 /usr/share/evenkeel-os/RPM-GPG-KEY-negativo17
install -Dm644 /ctx/evenkeel-os-codecs-setup.service /usr/lib/systemd/system/evenkeel-os-codecs-setup.service
systemctl enable evenkeel-os-flathub.service evenkeel-os-flatpak-apps.service evenkeel-os-codecs-setup.service
# Wallpapers: 7 in Settings, Appearance, each with a day picture for light mode and a night one for dark mode;
# the default is Main (sorts after Fedora's overrides). The old one stays for anyone who picked it.
install -Dm644 /ctx/branding/wallpaper.png /usr/share/backgrounds/evenkeel-os/wallpaper.png
install -Dm644 -t /usr/share/backgrounds/evenkeel-os /ctx/branding/wallpapers/*.jpg
install -Dm644 /ctx/branding/evenkeel-os.xml /usr/share/gnome-background-properties/evenkeel-os.xml
for f in $(grep -o '/usr/share/backgrounds/[^<]*' /usr/share/gnome-background-properties/evenkeel-os.xml); do
  [ -s "$f" ] || { echo "ERROR: Settings lists the wallpaper $f, which is missing"; exit 1; }
done
[ "$(grep -c '<filename-dark>' /usr/share/gnome-background-properties/evenkeel-os.xml)" = 7 ] \
  || { echo "ERROR: not every wallpaper has a night picture for dark mode"; exit 1; }
# New users' picture: the logo (AccountsService uses ~/.face); also offered in Settings, Users.
install -Dm644 /ctx/branding/evenkeel-os-user-picture.png /etc/skel/.face
install -Dm644 /ctx/branding/evenkeel-os-user-picture.png /usr/share/pixmaps/faces/evenkeel-os.png
# Lock screen password box in the accent color (one added rule; the tools are only needed while building).
dnf5 -y install glib2-devel
bash /ctx/evenkeel-os-shell-theme.sh
dnf5 -y remove glib2-devel
install -Dm644 /ctx/branding/zz-evenkeel-os-background.gschema.override /usr/share/glib-2.0/schemas/zz-evenkeel-os-background.gschema.override
install -Dm644 /ctx/zz-evenkeel-os-windows.gschema.override /usr/share/glib-2.0/schemas/zz-evenkeel-os-windows.gschema.override
install -Dm644 /ctx/zz-evenkeel-os-no-tour.gschema.override /usr/share/glib-2.0/schemas/zz-evenkeel-os-no-tour.gschema.override
install -Dm644 /ctx/zz-evenkeel-os-desktop.gschema.override /usr/share/glib-2.0/schemas/zz-evenkeel-os-desktop.gschema.override
install -Dm644 /ctx/zz-evenkeel-os-login.gschema.override /usr/share/glib-2.0/schemas/zz-evenkeel-os-login.gschema.override
install -Dm644 /ctx/branding/evenkeel-os-gdm-logo.png /usr/share/pixmaps/evenkeel-os-gdm-logo.png
glib-compile-schemas /usr/share/glib-2.0/schemas 2>&1 | { grep -v 'deprecated' || true; }
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.desktop.background picture-uri)
[ "$got" = "'file:///usr/share/backgrounds/evenkeel-os/main-day.jpg'" ] || { echo "ERROR: the default wallpaper is $got, not the EvenKeelOS one"; exit 1; }
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.desktop.background picture-uri-dark)
[ "$got" = "'file:///usr/share/backgrounds/evenkeel-os/main-night.jpg'" ] || { echo "ERROR: the default dark-mode wallpaper is $got, not the EvenKeelOS one"; exit 1; }
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.desktop.wm.preferences button-layout)
[ "$got" = "'appmenu:minimize,maximize,close'" ] || { echo "ERROR: windows have no minimize button by default ($got)"; exit 1; }
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.shell welcome-dialog-last-shown-version)
[ "$got" = "'4294967295'" ] || { echo "ERROR: GNOME's welcome popup would still open at first login ($got)"; exit 1; }
for a in $(GSETTINGS_BACKEND=memory gsettings get org.gnome.shell favorite-apps | tr -d "[],'"); do
  [ -s "/usr/share/applications/$a" ] || { echo "ERROR: the dock lists $a, which is not installed"; exit 1; }
done
rpm -q gnome-tour >/dev/null 2>&1 && { echo "ERROR: GNOME's tour app is still installed"; exit 1; }
[ "$(. /usr/lib/os-release; echo "$PRETTY_NAME")" = "EvenKeelOS" ] || { echo "ERROR: the system's display name is not EvenKeelOS"; exit 1; }
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.desktop.interface enable-hot-corners)
[ "$got" = "false" ] || { echo "ERROR: the hot corner is still on by default ($got)"; exit 1; }
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.desktop.interface accent-color)
[ "$got" = "'teal'" ] || { echo "ERROR: the default accent color is $got, not teal"; exit 1; }
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.desktop.interface show-battery-percentage)
[ "$got" = "true" ] || { echo "ERROR: the battery percentage is not shown by default ($got)"; exit 1; }
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.login-screen logo)
[ "$got" = "'/usr/share/pixmaps/evenkeel-os-gdm-logo.png'" ] && [ -s /usr/share/pixmaps/evenkeel-os-gdm-logo.png ] || { echo "ERROR: the login screen does not show the EvenKeelOS logo ($got)"; exit 1; }

# Folder icons in the accent color (teal by default): Adwaita Colors at a pinned commit, built from Fedora's own
# Adwaita icons; the helper switches sets when the accent color changes in Settings, Appearance.
git clone --quiet https://github.com/dpejoh/Adwaita-colors /tmp/adwaita-colors
git -C /tmp/adwaita-colors -c advice.detachedHead=false checkout --quiet 7d838af258da4ca05040760301d05140aa858145
[ "$(git -C /tmp/adwaita-colors rev-parse HEAD)" = 7d838af258da4ca05040760301d05140aa858145 ] \
  || { echo "ERROR: Adwaita Colors is not at the pinned commit"; exit 1; }
/tmp/adwaita-colors/setup -i -p /usr/share/icons blue teal green yellow orange red pink purple slate
install -Dm644 /tmp/adwaita-colors/LICENSE /usr/share/licenses/adwaita-colors/LICENSE
rm -rf /tmp/adwaita-colors
install -Dm755 /ctx/evenkeel-os-accent-icons /usr/libexec/evenkeel-os-accent-icons
install -Dm644 /ctx/evenkeel-os-accent-icons.desktop /etc/xdg/autostart/evenkeel-os-accent-icons.desktop
bash /ctx/check-accent-icons.sh

# Logo Menu 25.2, sha256-checked; its own schemas/ folder must go or it fails to load.
curl -fsSL --retry 3 -o /tmp/logomenu.zip "https://extensions.gnome.org/extension-data/logomenuaryan_k.v45.shell-extension.zip"
echo "78e6507d9aa033a17e7e2997ac5a1190b327b97ba019a313f1a9285854753ed2  /tmp/logomenu.zip" | sha256sum -c -
install -d /usr/share/gnome-shell/extensions/logomenu@aryan_k
python3 -I -m zipfile -e /tmp/logomenu.zip /usr/share/gnome-shell/extensions/logomenu@aryan_k
rm /tmp/logomenu.zip
chmod -R u=rwX,go=rX /usr/share/gnome-shell/extensions/logomenu@aryan_k
install -Dm644 /usr/share/gnome-shell/extensions/logomenu@aryan_k/schemas/org.gnome.shell.extensions.logo-menu.gschema.xml \
  /usr/share/glib-2.0/schemas/org.gnome.shell.extensions.logo-menu.gschema.xml
rm -r /usr/share/gnome-shell/extensions/logomenu@aryan_k/schemas
glib-compile-schemas /usr/share/glib-2.0/schemas 2>&1 | { grep -v 'deprecated' || true; }
gnome_shell=$(rpm -q --qf '%{VERSION}' gnome-shell | cut -d. -f1)
grep -q "\"$gnome_shell\"" /usr/share/gnome-shell/extensions/logomenu@aryan_k/metadata.json || { echo "ERROR: Logo Menu 25.2 does not support GNOME $gnome_shell"; exit 1; }
install -Dm644 /ctx/branding/logo-EvenKeel-mark.svg /usr/share/evenkeel-os/logo-menu-icon.svg
install -Dm644 /ctx/evenkeel-os-logo-menu.dconf /etc/dconf/db/distro.d/50-evenkeel-os-logo-menu
command -v bazaar >/dev/null && command -v ghostty >/dev/null || { echo "ERROR: Logo Menu's software center (bazaar) or terminal (ghostty) is missing"; exit 1; }

# Windows-style layout: Dash to Panel from Fedora, ArcMenu 70.0 sha256-checked, its schemas/ folder moved out.
dnf5 -y install gnome-shell-extension-dash-to-panel
curl -fsSL --retry 3 -o /tmp/arcmenu.zip "https://extensions.gnome.org/extension-data/arcmenuarcmenu.com.v74.shell-extension.zip"
echo "ef414c90dcb5f2b0c6ccb5f8e59fd9963c584789d3d8d26740ddb731100c4b40  /tmp/arcmenu.zip" | sha256sum -c -
install -d /usr/share/gnome-shell/extensions/arcmenu@arcmenu.com
python3 -I -m zipfile -e /tmp/arcmenu.zip /usr/share/gnome-shell/extensions/arcmenu@arcmenu.com
rm /tmp/arcmenu.zip
chmod -R u=rwX,go=rX /usr/share/gnome-shell/extensions/arcmenu@arcmenu.com
install -Dm644 /usr/share/gnome-shell/extensions/arcmenu@arcmenu.com/schemas/org.gnome.shell.extensions.arcmenu.gschema.xml \
  /usr/share/glib-2.0/schemas/org.gnome.shell.extensions.arcmenu.gschema.xml
rm -r /usr/share/gnome-shell/extensions/arcmenu@arcmenu.com/schemas
glib-compile-schemas /usr/share/glib-2.0/schemas 2>&1 | { grep -v 'deprecated' || true; }
for e in arcmenu@arcmenu.com dash-to-panel@jderose9.github.com; do
  grep -q "\"$gnome_shell\"" "/usr/share/gnome-shell/extensions/$e/metadata.json" || { echo "ERROR: $e does not support GNOME $gnome_shell"; exit 1; }
done
install -Dm644 /ctx/evenkeel-os-windows-layout.dconf /etc/dconf/db/distro.d/50-evenkeel-os-windows-layout
install -Dm755 /ctx/evenkeel-os-layout /usr/bin/evenkeel-os-layout

# Our tools in Show Apps' Utilities folder.
install -Dm644 /ctx/evenkeel-os-app-folders.dconf /etc/dconf/db/distro.d/50-evenkeel-os-app-folders
dconf update
for a in evenkeel-os-tools evenkeel-os-update evenkeel-os-install-package evenkeel-os-remove-apps evenkeel-os-repair-boxes evenkeel-os-login-apps evenkeel-os-codecs; do
  HOME=/tmp dconf read /org/gnome/desktop/app-folders/folders/Utilities/apps | grep -q "'$a.desktop'" || { echo "ERROR: $a is not in the Utilities folder"; exit 1; }
done
# The login screen reads its settings through the gdm profile; nothing there may undo the teal accent.
got=$(HOME=/tmp DCONF_PROFILE=gdm gsettings get org.gnome.desktop.interface accent-color)
[ "$got" = "'teal'" ] || { echo "ERROR: the login screen's accent color is $got, not teal"; exit 1; }
# Check Logo Menu's defaults through its schema (path has a capital L).
[ ! -e /usr/share/gnome-shell/extensions/logomenu@aryan_k/schemas ] || { echo "ERROR: Logo Menu still has its own schemas/ folder, so it would fail to start"; exit 1; }
for k in "org.gnome.shell enabled-extensions ['logomenu@aryan_k']" \
         "org.gnome.shell.extensions.logo-menu menu-button-software-center 'bazaar'" \
         "org.gnome.shell.extensions.logo-menu menu-button-terminal 'ghostty'" \
         "org.gnome.shell.extensions.logo-menu menu-button-system-monitor 'flatpak run net.nokyan.Resources'" \
         "org.gnome.shell.extensions.logo-menu use-custom-icon true" \
         "org.gnome.shell.extensions.logo-menu custom-icon-path '/usr/share/evenkeel-os/logo-menu-icon.svg'" \
         "org.gnome.shell.extensions.logo-menu show-activities-button false" \
         "org.gnome.shell.extensions.logo-menu hide-forcequit true"; do
  read -r schema key want <<<"$k"
  got=$(HOME=/tmp gsettings get "$schema" "$key")
  [ "$got" = "$want" ] || { echo "ERROR: Logo Menu default $schema $key is $got, not $want"; exit 1; }
done

# Check the Windows-style layout defaults and the switch.
for k in "org.gnome.shell.extensions.arcmenu menu-layout 'arcmenu'" \
         "org.gnome.shell.extensions.arcmenu default-menu-view 'Categories_List'" \
         "org.gnome.shell.extensions.arcmenu menu-button-icon '/usr/share/evenkeel-os/logo-menu-icon.svg'" \
         "org.gnome.shell.extensions.arcmenu update-notifier-enabled false" \
         "org.gnome.shell.extensions.dash-to-panel stockgs-keep-top-panel false" \
         "org.gnome.shell.extensions.dash-to-panel hide-overview-on-startup true"; do
  read -r schema key want <<<"$k"
  got=$(HOME=/tmp gsettings get "$schema" "$key")
  [ "$got" = "$want" ] || { echo "ERROR: Windows layout default $schema $key is $got, not $want"; exit 1; }
done
HOME=/tmp gsettings get org.gnome.shell.extensions.dash-to-panel panel-element-positions | grep -q '"showAppsButton","visible":false' || { echo "ERROR: the bottom bar would show its own app-grid button"; exit 1; }
shortcuts=$(HOME=/tmp gsettings get org.gnome.shell.extensions.arcmenu application-shortcuts | grep -o "'[^']*[.]desktop'" | tr -d "'")
[ "$(wc -w <<<"$shortcuts")" = 3 ] || { echo "ERROR: the start menu does not have its three shortcuts"; exit 1; }
for a in $shortcuts; do
  [ -s "/usr/share/applications/$a" ] || { echo "ERROR: the start menu lists $a, which is not installed"; exit 1; }
done
t=$(mktemp -d)
HOME=$t GSETTINGS_BACKEND=keyfile evenkeel-os-layout windows
[ "$(HOME=$t GSETTINGS_BACKEND=keyfile evenkeel-os-layout)" = windows ] || { echo "ERROR: evenkeel-os-layout does not switch to the Windows layout"; exit 1; }
HOME=$t GSETTINGS_BACKEND=keyfile evenkeel-os-layout current
[ "$(HOME=$t GSETTINGS_BACKEND=keyfile evenkeel-os-layout)" = current ] || { echo "ERROR: evenkeel-os-layout does not switch back"; exit 1; }
echo 1 | HOME=$t GSETTINGS_BACKEND=keyfile evenkeel-os-tools layout >/dev/null
[ "$(HOME=$t GSETTINGS_BACKEND=keyfile evenkeel-os-layout)" = windows ] || { echo "ERROR: System Tools' Desktop layout does not switch the layout"; exit 1; }
rm -rf "$t"

# Keep tuned from running bootc on every power-mode switch.
install -Dm644 /ctx/evenkeel-os-no-bootc.tuned.conf /usr/lib/tuned/profiles/evenkeel-os-no-bootc/tuned.conf
printf '%s\n' evenkeel-os-no-bootc > /etc/tuned/post_loaded_profile
python3 -I /ctx/check-tuned.py

# Check fingerprint login is on.
authselect current | grep -qw with-fingerprint || { echo "ERROR: authselect does not have with-fingerprint, so GNOME would not offer fingerprint login"; exit 1; }
grep -qw pam_fprintd.so /etc/pam.d/system-auth || { echo "ERROR: pam_fprintd is not in the PAM stack, so fingerprint would not be used"; exit 1; }
[ "$(systemctl is-enabled fprintd.service)" = enabled ] || { echo "ERROR: fprintd is not enabled, so it would not be running at login"; exit 1; }

# Firefox: Mozilla's home page and name, not Fedora's; fail if that changes.
ffprefs=/usr/lib64/firefox/browser/defaults/preferences/firefox-redhat-default-prefs.js
ffdist=/usr/lib64/firefox/distribution/distribution.ini
grep -q '^pref("browser.startup.homepage", *"https://start.fedoraproject.org/");' "$ffprefs" || { echo "ERROR: Firefox's Fedora home page setting was not found"; exit 1; }
grep -q '^pref("browser.newtabpage.pinned",' "$ffprefs" || { echo "ERROR: Firefox's Fedora tile setting was not found"; exit 1; }
sed -i -e 's|^pref("browser.startup.homepage", *"https://start.fedoraproject.org/");|pref("browser.startup.homepage", "about:home");|' \
       -e 's|^pref("browser.newtabpage.pinned",.*|pref("browser.newtabpage.pinned", "[]");|' "$ffprefs"
grep -q '^about=Mozilla Firefox for Fedora$' "$ffdist" || { echo "ERROR: Firefox's About text was not found"; exit 1; }
sed -i 's/^about=Mozilla Firefox for Fedora$/about=Mozilla Firefox/' "$ffdist"
grep -qi 'fedoraproject' "$ffprefs" && { echo "ERROR: Firefox still points at Fedora's pages"; exit 1; }
grep -qi '^about=.*fedora' "$ffdist" && { echo "ERROR: Firefox's About window still says Fedora"; exit 1; }

# fastfetch shows the EvenKeelOS logo.
install -Dm644 /ctx/fastfetch-logo.txt /usr/share/evenkeel-os/fastfetch-logo.txt
install -Dm644 /ctx/fastfetch-config.jsonc /etc/xdg/fastfetch/config.jsonc
out=$(HOME=/tmp fastfetch --pipe false -s OS 2>&1)
printf '%s' "$out" | grep -qF '_____________________' && printf '%s' "$out" | grep -qF 'EvenKeelOS' || { echo "ERROR: fastfetch does not show the EvenKeelOS logo"; printf '%s\n' "$out" | head -5; exit 1; }

install -Dm644 /ctx/$NAME.pub /etc/pki/containers/$NAME.pub
mkdir -p /etc/containers/registries.d
printf 'docker:\n  ghcr.io/ctsdownloads/%s:\n    use-sigstore-attachments: true\n' "$NAME" > /etc/containers/registries.d/$NAME.yaml
# Fedora 45 ships the default policy in /usr/share/containers; /etc overrides it.
[ -f /etc/containers/policy.json ] || cp /usr/share/containers/policy.json /etc/containers/policy.json
# Require our signature for our image; rpm-ostree refuses an accept-anything default.
jq --arg n "ghcr.io/ctsdownloads/$NAME" --arg k "/etc/pki/containers/$NAME.pub" '
  .default = [{"type":"reject"}]
  | reduce ("docker","docker-daemon","containers-storage","oci","oci-archive","dir","docker-archive","tarball","sif","atomic") as $t (.; .transports[$t][""] = [{"type":"insecureAcceptAnything"}])
  | .transports.docker[$n] = [{"type":"sigstoreSigned","keyPath":$k,"signedIdentity":{"type":"matchRepository"}}]
' /etc/containers/policy.json > /tmp/policy.json
mv /tmp/policy.json /etc/containers/policy.json
jq -e --arg n "ghcr.io/ctsdownloads/$NAME" '(.default | length == 1 and .[0].type == "reject") and (.transports.docker[$n][0].type == "sigstoreSigned") and (.transports.docker[""][0].type == "insecureAcceptAnything")' /etc/containers/policy.json > /dev/null || { echo "ERROR: the container policy is not what the signed rebase needs"; exit 1; }

# One shim on the disk: Fedora ships shimx64.efi twice (also as shim.efi), and some PCs' firmware turns the copy into
# an extra "Fedora" boot entry. bootupd and the USB boot from shimx64.efi only.
rm -f /usr/lib/efi/shim/*/EFI/fedora/shim.efi
ls /usr/lib/efi/shim/*/EFI/fedora/shimx64.efi >/dev/null || { echo "ERROR: Fedora's signed shim is missing"; exit 1; }
[ -z "$(ls /usr/lib/efi/shim/*/EFI/fedora/shim.efi 2>/dev/null)" ] || { echo "ERROR: the second shim (shim.efi) is still there"; exit 1; }

# Root helpers refuse hostile input, and no-password permissions stay with the person at the computer.
python3 -I /ctx/check-root-helpers.py
