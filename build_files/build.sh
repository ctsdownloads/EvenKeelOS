#!/bin/bash
set -ouex pipefail

NAME=evenkeel-os
fail() { echo "ERROR: $*"; exit 1; }

dnf5 -y install firefox v4l-utils xdg-terminal-exec
xargs -a /ctx/bluefin-packages.txt dnf5 -y install
# Default apps from Fedora (default-apps.txt); fails if any is missing.
grep -v '^#' /ctx/default-apps.txt | xargs dnf5 -y install
# Spell check in every translated language that has a dictionary (spellcheck-packages.txt); fails if any is missing.
grep -v '^#' /ctx/spellcheck-packages.txt | xargs dnf5 -y install
grep -v '^#' /ctx/spellcheck-packages.txt | xargs rpm -q >/dev/null || fail "a spell-check dictionary is missing"
# The Tajik dictionary Fedora doesn't package (extra-dictionaries.txt), sha256-checked.
grep -v '^#' /ctx/extra-dictionaries.txt | while read -r file sha url; do
  curl -fsSL --retry 3 -o "/tmp/$file" "$url"
  [[ $url == *format=TEXT ]] && base64 -d "/tmp/$file" > "/tmp/$file.d" && mv "/tmp/$file.d" "/tmp/$file"
  echo "$sha  /tmp/$file" | sha256sum -c -
  case $file in *README.txt) dir=/usr/share/licenses/evenkeel-os-dictionaries ;; *) dir=/usr/share/hunspell ;; esac
  install -Dm644 "/tmp/$file" "$dir/$file" && rm "/tmp/$file"
done
for d in bs_BA tg_TG; do [ -f "/usr/share/hunspell/$d.dic" ] || fail "no $d spell check"; done
# Ghostty (scottames/ghostty COPR) replaces Ptyxis as the default terminal.
curl -fsSL --retry 3 "https://copr.fedorainfracloud.org/coprs/scottames/ghostty/repo/fedora-$(rpm -E %fedora)/scottames-ghostty-fedora-$(rpm -E %fedora).repo" -o /etc/yum.repos.d/ghostty.repo
# Outside packages install at the exact versions in locked-versions.txt.
locked() { awk -v p="$1" '$1 == "copr" && $2 == p {print $3 "-" $4}' /ctx/locked-versions.txt; }
locked_failed() { fail "$1 did not install at its locked version (see docs/building.md)"; }
user_unit() {     # $1: target; the rest: user units, on for every account from /usr (not /etc)
  local target=$1 u
  shift
  install -Dm644 -t /usr/lib/systemd/user "${@/#//ctx/}"
  mkdir -p "/usr/lib/systemd/user/$target.wants"
  for u in "$@"; do ln -sfn "../$u" "/usr/lib/systemd/user/$target.wants/$u"; done
}
mapfile -t pkgs < <(locked scottames/ghostty)
dnf5 -y install "${pkgs[@]}" || locked_failed Ghostty
rm -f /etc/yum.repos.d/ghostty.repo
dnf5 -y remove ptyxis
rpm -q ptyxis >/dev/null 2>&1 && fail "Ptyxis is still installed"
install -Dm644 /ctx/xdg-terminals.list /etc/xdg/xdg-terminals.list
[ -s /usr/share/applications/com.mitchellh.ghostty.desktop ] || fail "Ghostty's launcher is missing, so xdg-terminal-exec has no terminal"
for p in $(grep -v '^#' /ctx/default-apps.txt) firefox nautilus ghostty nautilus-python gnome-control-center orca; do
  rpm -q "$p" >/dev/null || fail "default app $p is not installed"
done
# uupd, Homebrew and Bazaar from Universal Blue; Bazaar replaces GNOME Software.
curl -fsSL --retry 3 "https://copr.fedorainfracloud.org/coprs/ublue-os/packages/repo/fedora-$(rpm -E %fedora)/ublue-os-packages-fedora-$(rpm -E %fedora).repo" -o /etc/yum.repos.d/ublue-os-packages.repo
mapfile -t pkgs < <(locked ublue-os/packages)
dnf5 -y install "${pkgs[@]}" || locked_failed "uupd, Homebrew, ujust or Bazaar"
rm -f /etc/yum.repos.d/ublue-os-packages.repo
dnf5 -y remove gnome-software gnome-software-rpm-ostree
# No GNOME tour: its Welcome popup would cover the setup checklist.
dnf5 -y remove gnome-tour
for p in gnome-software gnome-software-rpm-ostree; do rpm -q "$p" >/dev/null 2>&1 && fail "$p is still installed"; done
rpm -q bazaar >/dev/null || fail "Bazaar is not installed"
[ -f /usr/share/gnome-shell/search-providers/io.github.kolunmi.Bazaar.search-provider.ini ] && [ -f /usr/share/dbus-1/services/io.github.kolunmi.Bazaar.SearchProvider.service ] || fail "Bazaar's Super-search provider is missing"
command -v ujust >/dev/null || fail 'ujust is missing'
# The shell tools show their words through gettext, in the person's language (domain evenkeel-os).
dnf5 -y install /usr/bin/gettext
command -v gettext >/dev/null || fail "gettext is missing: the shell tools can't show their words"
# Shared modules: windows and notices, network places, and what works on this computer (system versions too).
install -Dm644 -t /usr/lib/evenkeel-os /ctx/evenkeel_os_ui.py /ctx/evenkeel_os_network.py /ctx/evenkeel_os_health.py
python3 -I -c 'import sys; sys.path.insert(0, "/usr/lib/evenkeel-os"); import evenkeel_os_ui, evenkeel_os_health' \
  || fail "the shared modules do not load"
# Started from Wheelhouse, a tool's windows show inside it through evenkeel-os-dialog.
install -Dm755 /ctx/evenkeel-os-dialog /usr/libexec/evenkeel-os-dialog
python3 -I /ctx/check-dialogs.py /ctx /usr/libexec/evenkeel-os-dialog
# System Update: uupd with a progress window, no password (uupd's polkit rule, narrowed to the person at the computer).
install -Dm644 /ctx/40-evenkeel-os-uupd.rules /usr/share/polkit-1/rules.d/40-evenkeel-os-uupd.rules
install -Dm755 /ctx/evenkeel-os-update /usr/bin/evenkeel-os-update
install -Dm755 /ctx/evenkeel-os-update-helper /usr/libexec/evenkeel-os-update-helper
echo '{"deployments": [{"staged": true}]}' | /usr/libexec/evenkeel-os-update-helper staged \
  || fail "the System Update helper does not run"
install -Dm644 /ctx/evenkeel-os-update.desktop /usr/share/applications/evenkeel-os-update.desktop
# Install Package File: .rpm and .deb apps go into Fedora and Ubuntu boxes.
install -Dm755 /ctx/evenkeel-os-packages /usr/bin/evenkeel-os-packages
install -d /usr/lib/evenkeel-os/evenkeel_os_packages
install -m644 /ctx/evenkeel_os_packages/*.py /usr/lib/evenkeel-os/evenkeel_os_packages/
# Its root helpers (hardware rules, VPNs) go in first: its parts read their rules and lists from them.
install -Dm755 /ctx/evenkeel-os-hwrules /usr/libexec/evenkeel-os-hwrules
install -Dm755 /ctx/evenkeel-os-vpn /usr/libexec/evenkeel-os-vpn
python3 -I -c 'import sys, pkgutil, importlib; sys.path.insert(0, "/usr/lib/evenkeel-os"); import evenkeel_os_packages as p
[importlib.import_module("evenkeel_os_packages." + m.name) for m in pkgutil.iter_modules(p.__path__)]' \
  || fail "Install Package File's parts do not load"
# Starts box apps from Show Apps and stops them on Quit.
install -Dm755 /ctx/evenkeel-os-box-run /usr/libexec/evenkeel-os-box-run
install -Dm644 /ctx/io.github.ctsdownloads.evenkeel-os.hwrules.policy /usr/share/polkit-1/actions/io.github.ctsdownloads.evenkeel-os.hwrules.policy
# Get a VPN: Mullvad, Proton, IVPN and NordVPN from their companies' own download sources, signed by pinned keys.
install -Dm644 /ctx/vpns.json /usr/share/evenkeel-os/vpns.json
install -Dm644 -t /usr/share/evenkeel-os/vpn-keys /ctx/vpn-keys/*.asc
install -Dm644 /ctx/io.github.ctsdownloads.evenkeel-os.vpn.policy \
  /usr/share/polkit-1/actions/io.github.ctsdownloads.evenkeel-os.vpn.policy
(GNUPGHOME=$(mktemp -d); export GNUPGHOME; python3 -I /ctx/check-vpns.py; rc=$?; rm -rf "$GNUPGHOME"; exit $rc) \
  || fail 'Get a VPN is not set up right'
# Apps added to the system by name (VPNs, codecs) are checked daily for newer versions in their download sources.
install -Dm755 /ctx/evenkeel-os-app-updates /usr/libexec/evenkeel-os-app-updates
install -Dm644 /ctx/evenkeel-os-app-updates.service /usr/lib/systemd/system/evenkeel-os-app-updates.service
install -Dm644 /ctx/evenkeel-os-app-updates.timer /usr/lib/systemd/system/evenkeel-os-app-updates.timer
# A newly picked language: Flatpak apps get its translations within minutes, not at the next daily update.
install -Dm755 /ctx/evenkeel-os-flatpak-languages /usr/libexec/evenkeel-os-flatpak-languages
install -Dm644 -t /usr/lib/systemd/system \
  /ctx/evenkeel-os-flatpak-languages.service /ctx/evenkeel-os-flatpak-languages.timer \
  /ctx/evenkeel-os-flatpak-languages.path
# Dates, times and month names follow the account's language after a change.
install -Dm755 /ctx/evenkeel-os-language-follow /usr/libexec/evenkeel-os-language-follow
user_unit graphical-session.target evenkeel-os-language-follow.service
user_unit graphical-session-pre.target evenkeel-os-bazaar-language.service
# Wheelhouse, with a root helper for the jobs that change the system.
install -Dm755 /ctx/evenkeel-os-tools /usr/bin/evenkeel-os-tools
install -Dm755 /ctx/evenkeel-os-tools-admin /usr/libexec/evenkeel-os-tools-admin
install -Dm644 /ctx/io.github.ctsdownloads.evenkeel-os.tools.policy /usr/share/polkit-1/actions/io.github.ctsdownloads.evenkeel-os.tools.policy
# Certificate alerts: each person's own daily check (no admin rights), switched on from /usr for every account.
install -Dm755 /ctx/evenkeel-os-certs /usr/libexec/evenkeel-os-certs
install -Dm644 -t /usr/lib/systemd/user /ctx/evenkeel-os-certs.service
user_unit timers.target evenkeel-os-certs.timer
# Removing an added certificate: its own polkit action (in the tools policy), with the password every time.
install -Dm755 /ctx/evenkeel-os-cert-remove /usr/libexec/evenkeel-os-cert-remove
# The trusted list follows Fedora's at every start, even after a certificate was added.
install -Dm644 /ctx/evenkeel-os-ca-trust.service /usr/lib/systemd/system/evenkeel-os-ca-trust.service
ln -sfn ../evenkeel-os-ca-trust.service /usr/lib/systemd/system/multi-user.target.wants/evenkeel-os-ca-trust.service
[ -f /usr/lib/systemd/system/multi-user.target.wants/evenkeel-os-ca-trust.service ] && [ -x /usr/bin/update-ca-trust ] \
  || fail "the trusted certificate list isn't rebuilt at every start"
python3 -I /ctx/check-certs.py
# Harmless Wheelhouse jobs need no password for an admin at the computer.
install -Dm755 /ctx/evenkeel-os-tools-safe /usr/libexec/evenkeel-os-tools-safe
# Automatic updates pause for 3 days after an undo; System Update itself is never paused.
install -Dm755 /ctx/evenkeel-os-updates-pause-check /usr/libexec/evenkeel-os-updates-pause-check
install -Dm644 /ctx/50-evenkeel-os-pause.conf /usr/lib/systemd/system/uupd.service.d/50-evenkeel-os-pause.conf
grep -qx 'ExecCondition=/usr/libexec/evenkeel-os-updates-pause-check' /usr/lib/systemd/system/uupd.service.d/50-evenkeel-os-pause.conf || fail "automatic updates do not check for a pause"
[ ! -e /usr/lib/systemd/system/uupd-manual.service.d ] || fail "System Update's own run has a drop-in; check it is not paused"
pause=/var/lib/evenkeel-os/updates-paused-until
mkdir -p "${pause%/*}"
echo $(( $(date +%s) + 3600 )) > "$pause"
! /usr/libexec/evenkeel-os-updates-pause-check || fail "a pause does not stop automatic updates"
echo $(( $(date +%s) - 1 )) > "$pause"
/usr/libexec/evenkeel-os-updates-pause-check && [ ! -e "$pause" ] || fail "an ended pause is not cleared"
rmdir --ignore-fail-on-non-empty "${pause%/*}"
install -Dm644 /ctx/50-evenkeel-os.rules /usr/share/polkit-1/rules.d/50-evenkeel-os.rules
python3 -c 'import xml.dom.minidom,sys; [xml.dom.minidom.parse(f) for f in sys.argv[1:]]' \
  /ctx/io.github.ctsdownloads.evenkeel-os.tools.policy /ctx/io.github.ctsdownloads.evenkeel-os.codecs.policy \
  /ctx/io.github.ctsdownloads.evenkeel-os.vpn.policy \
  || fail "a Wheelhouse, codecs or VPN polkit policy is not valid XML"
# Keep the disk unlock note in step with the disk at every start.
install -Dm644 /ctx/evenkeel-os-disk-unlock-check.service /usr/lib/systemd/system/evenkeel-os-disk-unlock-check.service
systemctl enable evenkeel-os-disk-unlock-check.service
install -Dm644 /ctx/evenkeel-os-tools.desktop /usr/share/applications/evenkeel-os-tools.desktop
install -Dm644 -t /usr/share/icons/hicolor/scalable/apps /ctx/branding/evenkeel-os-wheelhouse.svg
gtk-update-icon-cache -f /usr/share/icons/hicolor
grep -qa evenkeel-os-wheelhouse /usr/share/icons/hicolor/icon-theme.cache \
  || fail "Wheelhouse's icon isn't in the icon cache"
grep -qx "Icon=evenkeel-os-wheelhouse" /usr/share/applications/evenkeel-os-tools.desktop && grep -qx "Name=Wheelhouse" \
  /usr/share/applications/evenkeel-os-tools.desktop || fail "Wheelhouse's launcher has the wrong name or icon"
# The setup checklist opens once at a new user's first login.
install -Dm644 /ctx/evenkeel-os-setup-checklist.desktop /etc/xdg/autostart/evenkeel-os-setup-checklist.desktop
install -Dm644 /ctx/evenkeel-os-rolled-back.desktop /etc/xdg/autostart/evenkeel-os-rolled-back.desktop
rm -f /etc/xdg/autostart/evenkeel-os-codecs-prompt.desktop
# Change list for System Update (empty in local builds).
install -Dm644 /dev/null /usr/share/evenkeel-os/changes.txt
[ -f /ctx/changes.txt ] && install -Dm644 /ctx/changes.txt /usr/share/evenkeel-os/changes.txt
# Microphones start at 50%; fail if WirePlumber drops the setting.
install -Dm644 /ctx/60-evenkeel-os-mic.conf /usr/share/wireplumber/wireplumber.conf.d/60-evenkeel-os-mic.conf
grep -q 'device.routes.default-source-volume' /usr/share/wireplumber/wireplumber.conf || fail "WirePlumber no longer has device.routes.default-source-volume"
for c in fwupdmgr systemd-cryptenroll cryptsetup flatpak podman gnome-control-center; do command -v "$c" >/dev/null || fail "Wheelhouse needs $c"; done
install -Dm644 /ctx/evenkeel-os-install-package.desktop /usr/share/applications/evenkeel-os-install-package.desktop
install -Dm644 /ctx/evenkeel-os-windows-program.desktop /usr/share/applications/evenkeel-os-windows-program.desktop
install -Dm644 /ctx/evenkeel-os-zoom-link.desktop /usr/share/applications/evenkeel-os-zoom-link.desktop
install -Dm644 /ctx/evenkeel-os-remove-apps.desktop /usr/share/applications/evenkeel-os-remove-apps.desktop
install -Dm644 /ctx/evenkeel-os-repair-boxes.desktop /usr/share/applications/evenkeel-os-repair-boxes.desktop
install -Dm644 /ctx/evenkeel-os-login-apps.desktop /usr/share/applications/evenkeel-os-login-apps.desktop
# At login, once: say when a package added to the system is ready.
install -Dm644 /ctx/evenkeel-os-packages-after-restart.desktop /etc/xdg/autostart/evenkeel-os-packages-after-restart.desktop
# Network safety: each network is Home, Work or a Public place (its firewall zone); a new one is a Public place.
for z in home work public; do install -Dm644 "/ctx/firewall/evenkeel-$z.xml" "/usr/lib/firewalld/zones/evenkeel-$z.xml"; done
firewall-offline-cmd --set-default-zone=evenkeel-public
# Let an app in, Open a port: what each place lets in beyond its own settings, and the list of apps to pick from.
install -Dm644 -t /usr/lib/evenkeel-os /ctx/evenkeel_os_letin.py /ctx/evenkeel_os_letin_page.py
python3 -I /ctx/make-let-in-apps.py /usr/lib/evenkeel-os /ctx/let-in-checked.txt
# Once, on computers installed earlier: Work lets nothing in, like a Public place.
install -Dm644 /ctx/evenkeel-os-work-update.service /usr/lib/systemd/system/evenkeel-os-work-update.service
ln -sfn ../evenkeel-os-work-update.service \
  /usr/lib/systemd/system/multi-user.target.wants/evenkeel-os-work-update.service
# Make it yours: light and dark on a schedule and the wallpaper slideshow, applied at login and every 5 minutes.
install -Dm644 -t /usr/lib/evenkeel-os /ctx/evenkeel_os_appearance.py /ctx/evenkeel_os_yours.py
install -Dm755 /ctx/evenkeel-os-appearance /usr/bin/evenkeel-os-appearance
install -Dm644 -t /usr/lib/systemd/user /ctx/evenkeel-os-appearance.service
user_unit timers.target evenkeel-os-appearance.timer
install -Dm644 /ctx/evenkeel-os-appearance.desktop /etc/xdg/autostart/evenkeel-os-appearance.desktop
python3 -I /ctx/check-appearance.py /usr/lib/evenkeel-os
install -Dm755 /ctx/evenkeel-os-network-ask /usr/libexec/evenkeel-os-network-ask
install -Dm644 /ctx/evenkeel-os-network-ask.desktop /etc/xdg/autostart/evenkeel-os-network-ask.desktop
python3 -I /ctx/check-network.py
# The Network safety switches run these.
for f in /usr/bin/firewall-cmd /usr/bin/cupsctl /usr/lib/systemd/system/sshd.service; do
  [ -e "$f" ] || fail "Network safety needs $f"
done
# Shared folders: Samba, found through Avahi (Macs, Linux) and wsdd (Windows); off until turned on.
dnf5 -y install samba avahi wsdd policycoreutils
install -Dm644 /ctx/samba/smb.conf /etc/samba/smb.conf
install -Dm644 /dev/null /etc/samba/evenkeel-shares.conf
install -Dm644 /ctx/firewall/evenkeel-sharing.xml /usr/lib/firewalld/services/evenkeel-sharing.xml
install -Dm644 /ctx/samba/wsdd-evenkeel-os.conf /usr/lib/systemd/system/wsdd.service.d/50-evenkeel-os.conf
install -Dm755 /ctx/samba/50-evenkeel-os-sharing /usr/lib/NetworkManager/dispatcher.d/50-evenkeel-os-sharing
install -Dm644 /ctx/evenkeel_os_sharing.py /usr/lib/evenkeel-os/evenkeel_os_sharing.py
for u in smb nmb wsdd; do
  state=$(systemctl is-enabled "$u.service" 2>/dev/null || true)
  [ "$state" = disabled ] || fail "$u.service must start off, not $state"
done
for f in /usr/bin/smbpasswd /usr/bin/smbcontrol /usr/bin/testparm /usr/sbin/setsebool /usr/sbin/avahi-daemon \
         /usr/lib/systemd/system/smb.service /usr/lib/systemd/system/wsdd.service; do
  [ -e "$f" ] || fail "Shared folders needs $f"
done
python3 -I /ctx/check-sharing.py
# Boot options: kernel settings changed in Wheelhouse, through rpm-ostree.
install -Dm644 /ctx/evenkeel_os_bootopts.py /usr/lib/evenkeel-os/evenkeel_os_bootopts.py
install -Dm755 /ctx/evenkeel-os-boot-options /usr/libexec/evenkeel-os-boot-options
python3 -I /ctx/check-boot-options.py
# GNOME never runs autostart entries that name a startup phase; fail if ours do.
if grep -l '^X-GNOME-Autostart-Phase=' /etc/xdg/autostart/evenkeel-os-*.desktop 2>/dev/null; then
  fail "the autostart entries above name a GNOME startup phase, so they would never run at login"
fi
# Our default apps go in /etc/xdg; Fedora's gnome-mimeapps.list stays as is.
install -Dm644 /ctx/gnome-mimeapps.list /etc/xdg/gnome-mimeapps.list
grep -q '^text/plain=org.gnome.TextEditor.desktop$' /usr/share/applications/gnome-mimeapps.list || fail "Fedora's GNOME default apps file is missing or changed"
update-desktop-database /usr/share/applications
opens_in() {     # $1: the launcher; the rest: the file and link types it must open
  local app=$1 t
  shift
  for t in "$@"; do
    [[ "$(XDG_CURRENT_DESKTOP=GNOME gio mime "$t" | sed -n 1p)" == *"$app"* ]] || fail "$t does not open in $app"
  done
}
opens_in evenkeel-os-install-package.desktop application/x-rpm application/vnd.debian.binary-package
opens_in evenkeel-os-windows-program.desktop application/vnd.microsoft.portable-executable application/x-msi
opens_in evenkeel-os-zoom-link.desktop x-scheme-handler/zoommtg x-scheme-handler/zoomus
python3 -I /ctx/check-zoom-links.py || fail 'Zoom links do not turn into the right web addresses'
for c in distrobox podman flatpak rpm2archive pkexec zenity dnf5; do command -v "$c" >/dev/null || fail "$c is missing: Install Package File needs it"; done
# distrobox 1.8.2.5 writes "ro:rslave", which podman rejects; the check fails when that line changes.
sed -i 's/:ro${rslave}"/:ro${rslave:+,rslave}"/' /usr/bin/distrobox-create
grep -qF ':ro${rslave:+,rslave}"' /usr/bin/distrobox-create && ! grep -qF ':ro${rslave}"' /usr/bin/distrobox-create \
  || fail "distrobox-create changed; check whether the ro,rslave fix is still needed"
mkdir -p /tmp/pkgtest && (cd /tmp/pkgtest && dnf5 -q download gnome-mines openvpn solaar-udev fedora-repos-archive)
python3 -I /ctx/check-packages.py /tmp/pkgtest || fail 'Install Package File does not read packages correctly'
python3 -I /ctx/check-printer-drivers.py /usr/lib/evenkeel-os || fail 'printer drivers are not recognized'
python3 -I /ctx/check-flatpak-places.py /usr/lib/evenkeel-os/evenkeel_os_packages /usr/bin /usr/libexec \
  || fail 'a flatpak install or uninstall does not say where it goes'
rm -rf /tmp/pkgtest
# Windows Program: an .exe or .msi offers a Linux replacement, from a list made fresh each build.
dnf5 -y install msitools python3-pefile
mkdir -p /tmp/winlist /usr/share/evenkeel-os
# ArtCraft apps install only when signed by ArtCraft's release key, pinned here by its fingerprint.
GNUPGHOME=$(mktemp -d)
export GNUPGHOME
gpg --batch --quiet --dearmor -o /usr/share/evenkeel-os/artcraft-keyring.gpg /ctx/artcraft-release-key.asc
gpg --batch --show-keys --with-colons /usr/share/evenkeel-os/artcraft-keyring.gpg \
  | grep -qx "fpr:::::::::$(python3 -I -c 'import sys; sys.path.insert(0, "/usr/lib/evenkeel-os")
from evenkeel_os_packages.artcraft import FINGERPRINT; print(FINGERPRINT)'):" \
  || fail "the ArtCraft release key is not the pinned one"
rm -rf "$GNUPGHOME"
unset GNUPGHOME
# The workflow downloads these (keeping the last copy if a site is down); a local build downloads them here.
data=/ctx/windows-data
[ -d "$data" ] || { data=/tmp/winlist/data; /ctx/fetch-windows-data.sh "$data"; }
python3 -I -m zipfile -e "$data/source.msix" /tmp/winlist/msix
python3 -I /ctx/make-windows-list.py /tmp/winlist/msix/Public/index.db "$data/flathub.xml.gz" \
  /usr/share/swcatalog/xml/fedora.xml.gz /ctx/windows-replacements.json \
  "$data/ubuntu-main.yml.gz" "$data/ubuntu-universe.yml.gz" /usr/share/evenkeel-os/windows-apps.json
python3 -I /ctx/check-windows-programs.py "$data" \
  || fail 'Windows Program does not read installers correctly'
rm -rf /tmp/winlist
# Services on by default, including after the first boot.
printf 'enable brew-setup.service\nenable evenkeel-os-codecs-setup.service\nenable evenkeel-os-flathub.service\nenable evenkeel-os-flatpak-apps.service\ndisable flatpak-add-fedora-repos.service\nenable evenkeel-os-disk-unlock-check.service\nenable tailscaled.service\nenable podman-auto-update.timer\nenable uupd.timer\nenable greenboot-healthcheck.service\nenable greenboot-set-rollback-trigger.service\nenable evenkeel-os-app-updates.timer\nenable evenkeel-os-flatpak-languages.timer\nenable evenkeel-os-flatpak-languages.path\n' > /usr/lib/systemd/system-preset/80-evenkeel-os.preset
systemctl enable tailscaled.service podman-auto-update.timer uupd.timer brew-setup.service evenkeel-os-app-updates.timer \
  evenkeel-os-flatpak-languages.timer evenkeel-os-flatpak-languages.path
for u in tailscaled.service uupd.timer brew-setup.service evenkeel-os-app-updates.timer evenkeel-os-flatpak-languages.timer \
         evenkeel-os-flatpak-languages.path; do [ "$(systemctl is-enabled "$u")" = enabled ] || fail "$u is not enabled"; done
bash /ctx/rebrand.sh
# Automatic rollback: greenboot with our own checks. Fedora's default checks fail offline, so they stay out.
dnf5 -y install greenboot
# 2 bad starts in a row, then back to the previous version (greenboot's default is 4).
sed -i 's/^GREENBOOT_MAX_BOOT_ATTEMPTS=.*/GREENBOOT_MAX_BOOT_ATTEMPTS=1/' /etc/greenboot/greenboot.conf
grep -qx 'GREENBOOT_MAX_BOOT_ATTEMPTS=1' /etc/greenboot/greenboot.conf || fail "greenboot's retry count isn't 1"
# greenboot's boot menu file lacks a final line break, so bootupd joins its last command to the next line.
gbcfg=/usr/lib/bootupd/grub2-static/configs.d/08_greenboot.cfg
[ -z "$(tail -c1 "$gbcfg")" ] || echo >>"$gbcfg"
# Build the boot menu the way bootupd does at install, and check it.
menu=$(mktemp)
{ cat /usr/lib/bootupd/grub2-static/grub-static-pre.cfg
  for f in /usr/lib/bootupd/grub2-static/configs.d/*.cfg; do
    printf '\n### BEGIN %s ###\n' "${f##*/}"; cat "$f"; printf '### END %s ###\n' "${f##*/}"
  done; } >"$menu"
grep -q '[^[:space:]]### END' "$menu" && fail "a boot menu file runs into the next one"
grep -qx 'save_env boot_success' "$menu" || fail "the boot menu doesn't save boot_success"
grub2-script-check "$menu" || fail "the boot menu bootupd would write fails GRUB's syntax check"
rm -f "$menu"
! rpm -q greenboot-default-health-checks >/dev/null || fail "Fedora's default greenboot checks are installed; they fail offline"
install -Dm755 -t /usr/lib/greenboot/check/required.d /ctx/greenboot/00-evenkeel-os-test-quick.sh \
  /ctx/greenboot/05-evenkeel-os-settings.sh /ctx/greenboot/10-evenkeel-os-login-screen.sh \
  /ctx/greenboot/20-evenkeel-os-networking.sh /ctx/greenboot/30-evenkeel-os-desktop.sh \
  /ctx/greenboot/40-evenkeel-os-still-works.sh
# The save (95) runs last: the rollback note (90) reads the settings test's marker, which the save clears.
install -Dm755 -t /usr/lib/greenboot/green.d /ctx/greenboot/90-evenkeel-os-rolled-back.sh \
  /ctx/greenboot/93-evenkeel-os-health-record.sh /ctx/greenboot/95-evenkeel-os-settings-save.sh
install -Dm755 /ctx/greenboot/evenkeel-os-health /usr/libexec/evenkeel-os-health
install -Dm755 /ctx/greenboot/evenkeel-os-wait-started /usr/libexec/evenkeel-os-wait-started
install -Dm644 -t /usr/lib/systemd/system /ctx/greenboot/evenkeel-os-health-record.service
# The trial check against a made-up computer: what must count as broken, and what (unplugged, switched off) mustn't.
python3 -I /ctx/check-health.py /usr/lib/evenkeel-os
# The window it opens before a restart: the answers, the countdown and the password, with a made-up zenity.
python3 -I /ctx/check-restart-question.py /usr/bin/evenkeel-os-tools /usr/lib/evenkeel-os
# What the trial check asks must be in the image, under the names it uses.
for c in lpstat busctl uupd rpm-ostree flatpak firewall-cmd resolvectl testparm udevadm journalctl mount loginctl \
         systemd-run; do
  command -v "$c" >/dev/null || fail "the trial check needs $c"
done
grep -qx 'BusName=org.freedesktop.UPower.PowerProfiles' /usr/lib/systemd/system/tuned-ppd.service \
  || fail "tuned-ppd has a new bus name; update evenkeel_os_health.py"
for f in org.freedesktop.fwupd net.reactivated.Fprint; do
  [ -f "/usr/share/dbus-1/system-services/$f.service" ] \
    || fail "the trial check asks $f, which isn't in the image"
done
python3 -I -c 'import sys; sys.path.insert(0, "/usr/lib/evenkeel-os")
import evenkeel_os_health as h
ids = h.fprint_ids()
sys.exit(0 if len(ids) > 50 else f"ERROR: the trial check finds only {len(ids)} fingerprint readers in the udev lists")'
# Settings repair: a copy of /etc saved after each good start, put back from when important settings go missing.
install -Dm755 -t /usr/lib/greenboot/red.d /ctx/greenboot/50-evenkeel-os-settings-repair.sh
install -Dm755 /ctx/greenboot/evenkeel-os-settings /usr/libexec/evenkeel-os-settings
fb=/usr/lib/systemd/system/systemd-firstboot.service.d/50-evenkeel-os.conf
install -Dm644 /ctx/50-evenkeel-os-firstboot.conf "$fb"
[ "$(sed -n 's/^ExecStart=//p' "$fb" | tail -1)" = /usr/bin/systemd-firstboot ] \
  || fail "the first-start setup can still stop startup to ask questions"
# Wheelhouse's settings test runs as its own polkit action (in the tools policy), with the password every time.
install -Dm755 /ctx/greenboot/evenkeel-os-settings-test /usr/libexec/evenkeel-os-settings-test
for c in rsync unshare findmnt; do
  command -v "$c" >/dev/null || fail "the settings repair needs $c"
done
# greenboot writes its status file before any check, so a missing /etc/motd.d stops it (our drop-in makes it).
grep -aqF /etc/motd.d/boot-status /usr/libexec/greenboot/greenboot \
  || fail "greenboot no longer writes /etc/motd.d/boot-status; check 50-evenkeel-os-greenboot.conf"
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
  || fail "greenboot-set-rollback-trigger's stop steps aren't greenboot then evenkeel-os-greenboot-arm"
# rpm-ostreed stays running once started (it quits after 60 idle seconds otherwise), so greenboot can mark a trial.
sed -i 's/^#\?IdleExitTimeout=.*/IdleExitTimeout=0/' /etc/rpm-ostreed.conf
grep -qx "IdleExitTimeout=0" /etc/rpm-ostreed.conf || fail "rpm-ostreed.conf has no IdleExitTimeout"
# Test automatic rollback: each test copy breaks one real thing, switched on by its kernel argument only.
install -Dm755 /ctx/greenboot/evenkeel-os-test-fail /usr/libexec/evenkeel-os-test-fail
install -Dm644 /ctx/greenboot/50-evenkeel-os-test-gdm.conf /usr/lib/systemd/system/gdm.service.d/50-evenkeel-os-test.conf
install -Dm644 /ctx/greenboot/50-evenkeel-os-test-networkmanager.conf \
  /usr/lib/systemd/system/NetworkManager.service.d/50-evenkeel-os-test.conf
install -Dm644 /ctx/greenboot/50-evenkeel-os-test-shell.conf /usr/lib/systemd/user/org.gnome.Shell@user.service.d/50-evenkeel-os-test.conf
install -Dm644 /ctx/greenboot/50-evenkeel-os-test-cups.conf \
  /usr/lib/systemd/system/cups.service.d/50-evenkeel-os-test.conf
install -Dm644 /ctx/greenboot/50-evenkeel-os-test-firewalld.conf \
  /usr/lib/systemd/system/firewalld.service.d/50-evenkeel-os-test.conf
for u in ModemManager.service switcheroo-control.service; do
  install -Dm644 /ctx/greenboot/50-evenkeel-os-test-service.conf "/usr/lib/systemd/system/$u.d/50-evenkeel-os-test.conf"
done
# The "A system service fails" test breaks one of these, whichever runs; one must be switched on.
systemctl -q is-enabled ModemManager.service || systemctl -q is-enabled switcheroo-control.service \
  || fail "neither ModemManager nor switcheroo-control is switched on; pick another test service"
install -Dm644 -t /usr/lib/systemd/system /ctx/greenboot/evenkeel-os-test-stuck.service \
  /ctx/greenboot/evenkeel-os-test-freeze.service /ctx/greenboot/evenkeel-os-test-update.service
systemctl enable evenkeel-os-test-stuck.service evenkeel-os-test-freeze.service evenkeel-os-test-update.service
[ -x /usr/bin/false ] && [ -x /usr/bin/uupd ] \
  || fail "the update program test needs /usr/bin/false and /usr/bin/uupd"
for u in gdm.service NetworkManager.service evenkeel-os-test-stuck.service evenkeel-os-test-freeze.service \
         greenboot-healthcheck.service cups.service firewalld.service ModemManager.service switcheroo-control.service \
         evenkeel-os-test-update.service evenkeel-os-health-record.service; do
  systemd-analyze verify "$u" 2>&1 | grep -iE "evenkeel|greenboot" && fail "$u has a unit problem"
done
# The login-loop test needs the user desktop's own shell unit (the login screen uses org.gnome.Shell@gdm).
grep -qx 'Requires=org.gnome.Shell@user.service' /usr/lib/systemd/user/gnome-session@gnome.target.d/gnome.session.conf \
  || fail "GNOME's desktop no longer starts org.gnome.Shell@user.service; update the login-loop test"
# Also switched on from /usr, as their [Install] lines say, so deleting /etc can't switch them off.
for l in multi-user.target.wants/greenboot-healthcheck.service \
         greenboot-success.target.requires/greenboot-healthcheck.service \
         ostree-finalize-staged.service.requires/greenboot-set-rollback-trigger.service \
         multi-user.target.wants/evenkeel-os-boot-menu-repair.service \
         multi-user.target.wants/evenkeel-os-test-stuck.service \
         multi-user.target.wants/evenkeel-os-test-freeze.service \
         multi-user.target.wants/evenkeel-os-test-update.service; do
  mkdir -p "/usr/lib/systemd/system/${l%/*}"
  ln -sfn "../${l##*/}" "/usr/lib/systemd/system/$l"
  [ -f "/usr/lib/systemd/system/$l" ] || fail "/usr/lib/systemd/system/$l doesn't lead to its unit"
  u=${l##*/}; t=${l%/*}; t=${t%.*}; kind=${l%/*}; kind=${kind##*.}
  want=$([ "$kind" = wants ] && echo WantedBy || echo RequiredBy)
  grep -qx "$want=${t}" "/usr/lib/systemd/system/$u" || fail "$u's [Install] has no $want=$t"
done
python3 -I /ctx/check-settings-repair.py
# Normal starts never trip a test: with no test kernel argument every test step passes.
python3 -I /ctx/check-rollback-tests.py
for f in /usr/lib/greenboot/check/required.d/*-evenkeel-os-*.sh /usr/lib/greenboot/green.d/*-evenkeel-os-*.sh \
         /usr/lib/greenboot/red.d/*-evenkeel-os-*.sh \
         /usr/libexec/evenkeel-os-test-fail /usr/libexec/evenkeel-os-greenboot-arm /usr/libexec/evenkeel-os-boot-menu-repair \
         /usr/libexec/evenkeel-os-wait-started; do
  bash -n "$f" || fail "$f has a syntax error"
done
systemctl enable greenboot-healthcheck.service
for u in greenboot-healthcheck.service greenboot-set-rollback-trigger.service; do
  [ "$(systemctl is-enabled "$u")" = enabled ] || fail "$u is not enabled"
done
# bootupd copies this into the boot menu at install; without it nothing counts failed starts.
grep -q boot_counter /usr/lib/bootupd/grub2-static/configs.d/08_greenboot.cfg || fail "greenboot's boot menu counter is missing"
# The rollback note looks for these lines in greenboot's log.
for t in 'Rollback successful' 'Rollback to previous deployment completed' 'deployment has been rolled back'; do
  grep -aqF "$t" /usr/libexec/greenboot/greenboot || fail "greenboot no longer logs \"$t\"; update 90-evenkeel-os-rolled-back.sh"
done
# TPM support in the boot image, for automatic disk unlock.
dnf5 -y install tpm2-tss
printf 'add_dracutmodules+=" tpm2-tss "\n' > /usr/lib/dracut/dracut.conf.d/90-evenkeel-os-tpm.conf
# An update can bring a newer libzstd without the matching zstd tool (Fedora's 1.6.0); match the tool first.
zv=$(rpm -q --qf '%{version}-%{release}\n' libzstd | head -1)
[ "$(rpm -q --qf '%{version}-%{release}\n' zstd | head -1)" = "$zv" ] || dnf5 -y install "zstd-$zv"
[ "$(echo ok | zstd -q | zstd -dq)" = ok ] || fail "zstd $zv does not run: no boot files"
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
grep -qx net.nokyan.Resources /usr/share/evenkeel-os/flathub-apps.txt || fail "Resources (net.nokyan.Resources) is not in the Flathub apps list, so the Logo Menu's system monitor would be missing"
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
# RPM Fusion for full codecs, copied in only when chosen; fail without its key.
install -Dm644 /ctx/rpmfusion-free.repo /usr/share/evenkeel-os/rpmfusion-free.repo
install -Dm644 /ctx/rpmfusion-free-updates.repo /usr/share/evenkeel-os/rpmfusion-free-updates.repo
[ -s "/usr/share/distribution-gpg-keys/rpmfusion/RPM-GPG-KEY-rpmfusion-free-fedora-$(rpm -E %fedora)" ] || fail 'the RPM Fusion signing key is missing'
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
  [ "$swap_ok" = 1 ] || fail "RPM Fusion's codecs do not install on Fedora $(rpm -E %fedora) yet, so \"Everything\" would fail for users. Wait for RPM Fusion, then rebuild."
  [ "$web_ok" = 1 ] || fail "Cisco's OpenH264 does not install in place of $STAND_IN, so \"Web video only\" would fail for users" )
install -Dm644 /ctx/evenkeel-os-codecs-setup.service /usr/lib/systemd/system/evenkeel-os-codecs-setup.service
systemctl enable evenkeel-os-flathub.service evenkeel-os-flatpak-apps.service evenkeel-os-codecs-setup.service
# Wallpapers: 7, each with a day and a night picture; the default is Main (sorts after Fedora's overrides).
install -Dm644 /ctx/branding/wallpaper.png /usr/share/backgrounds/evenkeel-os/wallpaper.png
install -Dm644 -t /usr/share/backgrounds/evenkeel-os /ctx/branding/wallpapers/*.jpg
install -Dm644 /ctx/branding/evenkeel-os.xml /usr/share/gnome-background-properties/evenkeel-os.xml
for f in $(grep -o '/usr/share/backgrounds/[^<]*' /usr/share/gnome-background-properties/evenkeel-os.xml); do
  [ -s "$f" ] || fail "Settings lists the wallpaper $f, which is missing"
done
[ "$(grep -c '<filename-dark>' /usr/share/gnome-background-properties/evenkeel-os.xml)" = 7 ] \
  || fail "not every wallpaper has a night picture for dark mode"
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
[ "$got" = "'file:///usr/share/backgrounds/evenkeel-os/main-day.jpg'" ] || fail "the default wallpaper is $got, not the EvenKeelOS one"
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.desktop.background picture-uri-dark)
[ "$got" = "'file:///usr/share/backgrounds/evenkeel-os/main-night.jpg'" ] || fail "the default dark-mode wallpaper is $got, not the EvenKeelOS one"
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.desktop.wm.preferences button-layout)
[ "$got" = "'appmenu:minimize,maximize,close'" ] || fail "windows have no minimize button by default ($got)"
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.shell welcome-dialog-last-shown-version)
[ "$got" = "'4294967295'" ] || fail "GNOME's welcome popup would still open at first login ($got)"
for a in $(GSETTINGS_BACKEND=memory gsettings get org.gnome.shell favorite-apps | tr -d "[],'"); do
  [ -s "/usr/share/applications/$a" ] || fail "the dock lists $a, which is not installed"
done
rpm -q gnome-tour >/dev/null 2>&1 && fail "GNOME's tour app is still installed"
[ "$(. /usr/lib/os-release; echo "$PRETTY_NAME")" = "EvenKeelOS" ] || fail "the system's display name is not EvenKeelOS"
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.desktop.interface enable-hot-corners)
[ "$got" = "false" ] || fail "the hot corner is still on by default ($got)"
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.desktop.interface accent-color)
[ "$got" = "'teal'" ] || fail "the default accent color is $got, not teal"
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.desktop.interface show-battery-percentage)
[ "$got" = "true" ] || fail "the battery percentage is not shown by default ($got)"
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.login-screen logo)
[ "$got" = "'/usr/share/pixmaps/evenkeel-os-gdm-logo.png'" ] && [ -s /usr/share/pixmaps/evenkeel-os-gdm-logo.png ] || fail "the login screen does not show the EvenKeelOS logo ($got)"

# Folder icons in the accent color (teal by default): Adwaita Colors at a pinned commit.
git clone --quiet https://github.com/dpejoh/Adwaita-colors /tmp/adwaita-colors
git -C /tmp/adwaita-colors -c advice.detachedHead=false checkout --quiet 7d838af258da4ca05040760301d05140aa858145
[ "$(git -C /tmp/adwaita-colors rev-parse HEAD)" = 7d838af258da4ca05040760301d05140aa858145 ] \
  || fail "Adwaita Colors is not at the pinned commit"
/tmp/adwaita-colors/setup -i -p /usr/share/icons blue teal green yellow orange red pink purple slate
install -Dm644 /tmp/adwaita-colors/LICENSE /usr/share/licenses/adwaita-colors/LICENSE
rm -rf /tmp/adwaita-colors
install -Dm755 /ctx/evenkeel-os-accent-icons /usr/libexec/evenkeel-os-accent-icons
install -Dm644 /ctx/evenkeel-os-accent-icons.desktop /etc/xdg/autostart/evenkeel-os-accent-icons.desktop
bash /ctx/check-accent-icons.sh

# Logo Menu, sha256-checked; its own schemas/ folder must go or it fails to load.
extension() {     # $1: uuid, $2: its schema file; extensions.gnome.org's zip at its locked version and sha256
  local dir=/usr/share/gnome-shell/extensions/$1 version sha
  read -r version sha < <(awk -v u="$1" '$1 == "gnome-extension" && $2 == u {print $3, $4}' /ctx/locked-versions.txt)
  curl -fsSL --retry 3 -o /tmp/extension.zip "https://extensions.gnome.org/extension-data/${1//@/}.v$version.shell-extension.zip"
  echo "$sha  /tmp/extension.zip" | sha256sum -c -
  install -d "$dir"
  python3 -I -m zipfile -e /tmp/extension.zip "$dir"
  rm /tmp/extension.zip
  chmod -R u=rwX,go=rX "$dir"
  install -Dm644 "$dir/schemas/$2" "/usr/share/glib-2.0/schemas/$2"
  rm -r "$dir/schemas"
}
extension logomenu@aryan_k org.gnome.shell.extensions.logo-menu.gschema.xml
# A Wheelhouse entry under Extensions; Logo Menu has no setting for extra entries. Fails if its menu code changes.
python3 -I - /usr/share/gnome-shell/extensions/logomenu@aryan_k/extension.js <<'PY'
import sys
path = sys.argv[1]
after = "        this._addItem(new MenuItem(_('Extensions'), () => this._openExtensionsApp()));\n"
entry = "        this._addItem(new MenuItem('Wheelhouse', () => Util.spawn(['/usr/bin/evenkeel-os-tools'])));\n"
with open(path) as f:
    js = f.read()
if js.count(after) != 1 or entry in js:
    sys.exit("ERROR: Logo Menu's menu code changed, so Wheelhouse can't be added to it")
with open(path, "w") as f:
    f.write(js.replace(after, after + entry))
PY
grep -qF "new MenuItem('Wheelhouse'," /usr/share/gnome-shell/extensions/logomenu@aryan_k/extension.js \
  || fail 'the Logo Menu has no Wheelhouse entry'
glib-compile-schemas /usr/share/glib-2.0/schemas 2>&1 | { grep -v 'deprecated' || true; }
gnome_shell=$(rpm -q --qf '%{VERSION}' gnome-shell | cut -d. -f1)
grep -q "\"$gnome_shell\"" /usr/share/gnome-shell/extensions/logomenu@aryan_k/metadata.json || fail "Logo Menu does not support GNOME $gnome_shell"
install -Dm644 /ctx/branding/logo-EvenKeel-mark.svg /usr/share/evenkeel-os/logo-menu-icon.svg
install -Dm644 /ctx/evenkeel-os-logo-menu.dconf /etc/dconf/db/distro.d/50-evenkeel-os-logo-menu
command -v bazaar >/dev/null && command -v ghostty >/dev/null || fail "Logo Menu's software center (bazaar) or terminal (ghostty) is missing"

# Windows-style layout: Dash to Panel (from Fedora's build archive, signature checked) and ArcMenu, at locked versions.
d2p=$(awk '$1 == "fedora" && $3 == "gnome-shell-extension-dash-to-panel" {print $4}' /ctx/locked-versions.txt)
# gpg needs a home folder; the image's /root doesn't exist during the build, so it gets a temporary one.
GNUPGHOME=$(mktemp -d)
export GNUPGHOME
key=$(gpg --batch --show-keys --with-colons "/usr/share/pki/rpm-gpg/RPM-GPG-KEY-fedora-$(rpm -E %fedora)-primary" \
  | awk -F: '/^fpr/ {print tolower(substr($10, 33)); exit}')
rm -rf "$GNUPGHOME"
unset GNUPGHOME
[[ $key =~ ^[0-9a-f]{8}$ ]] || fail "can't read the Fedora signing key's id (got '$key')"
curl -fsSL --retry 3 -o /tmp/dash-to-panel.rpm "https://kojipkgs.fedoraproject.org/packages/\
gnome-shell-extension-dash-to-panel/${d2p%-*}/${d2p##*-}/data/signed/$key/noarch/gnome-shell-extension-dash-to-panel-$d2p.noarch.rpm"
rpmkeys --import "/usr/share/pki/rpm-gpg/RPM-GPG-KEY-fedora-$(rpm -E %fedora)-primary"
rpmkeys --checksig /tmp/dash-to-panel.rpm | grep -q 'signatures OK' \
  || fail "Dash to Panel does not carry Fedora's signature"
dnf5 -y install /tmp/dash-to-panel.rpm
rm /tmp/dash-to-panel.rpm
[ "$(rpm -q --qf '%{VERSION}-%{RELEASE}' gnome-shell-extension-dash-to-panel)" = "$d2p" ] || locked_failed "Dash to Panel"
extension arcmenu@arcmenu.com org.gnome.shell.extensions.arcmenu.gschema.xml
glib-compile-schemas /usr/share/glib-2.0/schemas 2>&1 | { grep -v 'deprecated' || true; }
for e in arcmenu@arcmenu.com dash-to-panel@jderose9.github.com; do
  grep -q "\"$gnome_shell\"" "/usr/share/gnome-shell/extensions/$e/metadata.json" || fail "$e does not support GNOME $gnome_shell"
done
install -Dm644 /ctx/evenkeel-os-windows-layout.dconf /etc/dconf/db/distro.d/50-evenkeel-os-windows-layout
install -Dm755 /ctx/evenkeel-os-layout /usr/bin/evenkeel-os-layout

# Wheelhouse in Show Apps' Utilities folder; the other tools' launchers are hidden but still open their files.
install -Dm644 /ctx/evenkeel-os-app-folders.dconf /etc/dconf/db/distro.d/50-evenkeel-os-app-folders
dconf update
HOME=/tmp dconf read /org/gnome/desktop/app-folders/folders/Utilities/apps | grep -q "'evenkeel-os-tools.desktop'" \
  || fail "Wheelhouse is not in the Utilities folder"
for a in evenkeel-os-update evenkeel-os-install-package evenkeel-os-remove-apps evenkeel-os-repair-boxes \
         evenkeel-os-login-apps evenkeel-os-codecs; do
  grep -qx 'NoDisplay=true' "/usr/share/applications/$a.desktop" \
    || fail "$a still shows in Show Apps; it belongs inside Wheelhouse"
done
install -Dm644 /ctx/evenkeel_os_dialogs.py /usr/lib/evenkeel-os/evenkeel_os_dialogs.py
install -Dm644 /ctx/evenkeel_os_panel.py /usr/lib/evenkeel-os/evenkeel_os_panel.py
# The EvenKeelOS guide in Wheelhouse, Get help; New to EvenKeelOS? at login after the setup checklist until ticked.
install -Dm644 /ctx/evenkeel_os_guide.py /usr/lib/evenkeel-os/evenkeel_os_guide.py
install -Dm644 /ctx/evenkeel-os-guide.desktop /etc/xdg/autostart/evenkeel-os-guide.desktop
python3 -I /ctx/check-panel.py \
  || fail 'the Wheelhouse window is missing a tool, an icon or a command'
# The login screen reads its settings through the gdm profile; nothing there may undo the teal accent.
got=$(HOME=/tmp DCONF_PROFILE=gdm gsettings get org.gnome.desktop.interface accent-color)
[ "$got" = "'teal'" ] || fail "the login screen's accent color is $got, not teal"
# Check Logo Menu's defaults through its schema (path has a capital L).
defaults() {      # $1: whose defaults; the rest: "schema key value", read through dconf
  local what=$1 k schema key want got
  shift
  for k in "$@"; do
    read -r schema key want <<<"$k"
    got=$(HOME=/tmp gsettings get "$schema" "$key")
    [ "$got" = "$want" ] || fail "$what default $schema $key is $got, not $want"
  done
}
defaults "Logo Menu" "org.gnome.shell enabled-extensions ['logomenu@aryan_k']" \
         "org.gnome.shell.extensions.logo-menu menu-button-software-center 'bazaar'" \
         "org.gnome.shell.extensions.logo-menu menu-button-terminal 'ghostty'" \
         "org.gnome.shell.extensions.logo-menu menu-button-system-monitor 'flatpak run net.nokyan.Resources'" \
         "org.gnome.shell.extensions.logo-menu use-custom-icon true" \
         "org.gnome.shell.extensions.logo-menu custom-icon-path '/usr/share/evenkeel-os/logo-menu-icon.svg'" \
         "org.gnome.shell.extensions.logo-menu show-activities-button false" \
         "org.gnome.shell.extensions.logo-menu hide-forcequit true"

# Check the Windows-style layout defaults and the switch.
defaults "Windows layout" "org.gnome.shell.extensions.arcmenu menu-layout 'arcmenu'" \
         "org.gnome.shell.extensions.arcmenu default-menu-view 'Categories_List'" \
         "org.gnome.shell.extensions.arcmenu menu-button-icon '/usr/share/evenkeel-os/logo-menu-icon.svg'" \
         "org.gnome.shell.extensions.arcmenu update-notifier-enabled false" \
         "org.gnome.shell.extensions.dash-to-panel stockgs-keep-top-panel false" \
         "org.gnome.shell.extensions.dash-to-panel hide-overview-on-startup true"
HOME=/tmp gsettings get org.gnome.shell.extensions.dash-to-panel panel-element-positions | grep -q '"showAppsButton","visible":false' || fail "the bottom bar would show its own app-grid button"
shortcuts=$(HOME=/tmp gsettings get org.gnome.shell.extensions.arcmenu application-shortcuts | grep -o "'[^']*[.]desktop'" | tr -d "'")
[ "$(wc -w <<<"$shortcuts")" = 3 ] || fail "the start menu does not have its three shortcuts"
for a in $shortcuts; do
  [ -s "/usr/share/applications/$a" ] || fail "the start menu lists $a, which is not installed"
done
t=$(mktemp -d)
HOME=$t GSETTINGS_BACKEND=keyfile evenkeel-os-layout windows
[ "$(HOME=$t GSETTINGS_BACKEND=keyfile evenkeel-os-layout)" = windows ] || fail "evenkeel-os-layout does not switch to the Windows layout"
HOME=$t GSETTINGS_BACKEND=keyfile evenkeel-os-layout current
[ "$(HOME=$t GSETTINGS_BACKEND=keyfile evenkeel-os-layout)" = current ] || fail "evenkeel-os-layout does not switch back"
echo 1 | HOME=$t GSETTINGS_BACKEND=keyfile evenkeel-os-tools layout >/dev/null
[ "$(HOME=$t GSETTINGS_BACKEND=keyfile evenkeel-os-layout)" = windows ] || fail "Wheelhouse's Desktop layout does not switch the layout"
rm -rf "$t"

# Keep tuned from running bootc on every power-mode switch.
install -Dm644 /ctx/evenkeel-os-no-bootc.tuned.conf /usr/lib/tuned/profiles/evenkeel-os-no-bootc/tuned.conf
printf '%s\n' evenkeel-os-no-bootc > /etc/tuned/post_loaded_profile
python3 -I /ctx/check-tuned.py

# Check fingerprint login is on.
authselect current | grep -qw with-fingerprint || fail "authselect does not have with-fingerprint, so GNOME would not offer fingerprint login"
grep -qw pam_fprintd.so /etc/pam.d/system-auth || fail "pam_fprintd is not in the PAM stack, so fingerprint would not be used"
[ "$(systemctl is-enabled fprintd.service)" = enabled ] || fail "fprintd is not enabled, so it would not be running at login"

# Firefox: Mozilla's home page and name, not Fedora's; fail if that changes.
ffprefs=/usr/lib64/firefox/browser/defaults/preferences/firefox-redhat-default-prefs.js
ffdist=/usr/lib64/firefox/distribution/distribution.ini
grep -q '^pref("browser.startup.homepage", *"https://start.fedoraproject.org/");' "$ffprefs" || fail "Firefox's Fedora home page setting was not found"
grep -q '^pref("browser.newtabpage.pinned",' "$ffprefs" || fail "Firefox's Fedora tile setting was not found"
sed -i -e 's|^pref("browser.startup.homepage", *"https://start.fedoraproject.org/");|pref("browser.startup.homepage", "about:home");|' \
       -e 's|^pref("browser.newtabpage.pinned",.*|pref("browser.newtabpage.pinned", "[]");|' "$ffprefs"
grep -q '^about=Mozilla Firefox for Fedora$' "$ffdist" || fail "Firefox's About text was not found"
sed -i 's/^about=Mozilla Firefox for Fedora$/about=Mozilla Firefox/' "$ffdist"
grep -qi 'fedoraproject' "$ffprefs" && fail "Firefox still points at Fedora's pages"
grep -qi '^about=.*fedora' "$ffdist" && fail "Firefox's About window still says Fedora"

# fastfetch shows the EvenKeelOS logo.
install -Dm644 /ctx/fastfetch-logo.txt /usr/share/evenkeel-os/fastfetch-logo.txt
install -Dm644 /ctx/fastfetch-config.jsonc /etc/xdg/fastfetch/config.jsonc
out=$(HOME=/tmp fastfetch --pipe false -s OS 2>&1)
printf '%s' "$out" | grep -qF '_____________________' && printf '%s' "$out" | grep -qF 'EvenKeelOS' || { echo "ERROR: fastfetch does not show the EvenKeelOS logo"; printf '%s\n' "$out" | head -5; exit 1; }

# EvenKeelOS's own translations (po/): message files, plus the translated names in its launchers and password prompts.
dnf5 -y install gettext
while read -r lang; do
  install -d "/usr/share/locale/$lang/LC_MESSAGES"
  msgfmt -c -o "/usr/share/locale/$lang/LC_MESSAGES/evenkeel-os.mo" "/ctx/po/$lang.po"
done < /ctx/po/LINGUAS
for f in /usr/share/applications/evenkeel-os-*.desktop /etc/xdg/autostart/evenkeel-os-*.desktop; do
  msgfmt --desktop -d /ctx/po --template="$f" -o "$f.new" || exit 1
  mv "$f.new" "$f"
done
for f in /usr/share/polkit-1/actions/io.github.ctsdownloads.evenkeel-os.*.policy; do
  GETTEXTDATADIRS=/ctx/po msgfmt --xml -d /ctx/po --template="$f" -o "$f.new" || exit 1
  mv "$f.new" "$f"
done
# Dash to Panel, ArcMenu, Logo Menu, Bazaar and Ghostty: their makers' translations, with ours filling the gaps.
bash /ctx/install-app-translations.sh /ctx/po
langs=$(grep -c . /ctx/po/LINGUAS)
[ "$(ls /usr/share/locale/*/LC_MESSAGES/evenkeel-os.mo | wc -l)" -eq "$langs" ] \
  || fail "not every language in po/LINGUAS has its messages"
grep -q '^Name\[de\]=' /usr/share/applications/evenkeel-os-tools.desktop \
  || fail "the launchers have no translated names"
grep -q 'xml:lang="de"' /usr/share/polkit-1/actions/io.github.ctsdownloads.evenkeel-os.tools.policy \
  || fail "the password prompts have no translated text"

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
jq -e --arg n "ghcr.io/ctsdownloads/$NAME" '(.default | length == 1 and .[0].type == "reject") and (.transports.docker[$n][0].type == "sigstoreSigned") and (.transports.docker[""][0].type == "insecureAcceptAnything")' /etc/containers/policy.json > /dev/null || fail "the container policy is not what the signed rebase needs"

# Fedora ships shim twice; some firmware makes shim.efi an extra boot entry. bootupd and the USB use shimx64.efi.
rm -f /usr/lib/efi/shim/*/EFI/fedora/shim.efi
ls /usr/lib/efi/shim/*/EFI/fedora/shimx64.efi >/dev/null || fail "Fedora's signed shim is missing"
[ -z "$(ls /usr/lib/efi/shim/*/EFI/fedora/shim.efi 2>/dev/null)" ] || fail "the second shim (shim.efi) is still there"

# Every package not signed by Fedora's key is on the locked list, at exactly that version.
python3 -I /ctx/check-locked-versions.py /ctx/locked-versions.txt \
  "/usr/share/pki/rpm-gpg/RPM-GPG-KEY-fedora-$(rpm -E %fedora)-primary"

# Root helpers refuse hostile input, and no-password permissions stay with the person at the computer.
python3 -I /ctx/check-root-helpers.py
