#!/usr/bin/bash
# Check every EvenKeelOS change is in the built images. Usage: iso/verify-image.sh [system] [live]
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
sys=${1-localhost/evenkeel-os}
live=${2-localhost/evenkeel-os-live}
logo_sum=$(sha256sum build_files/fastfetch-logo.txt | cut -d' ' -f1)
apps="$(grep -v '^#' build_files/default-apps.txt | tr '\n' ' ')firefox nautilus ghostty gnome-control-center orca bazaar"

# Runs checks inside an image; prints PASS or FAIL per check.
ok='ok() { if eval "$2" >/dev/null 2>&1; then echo "PASS: $1"; else echo "FAIL: $1"; fi; }'
run_in() { sudo podman run --rm --pull=never --network=none --entrypoint /usr/bin/bash -e LOGO_SUM="$logo_sum" -e APPS="$apps" "$1" -c "$ok
$2"; }

system_checks=$(cat <<'EOF'
gs() { GSETTINGS_BACKEND=memory gsettings get "$1" "$2"; }
none() { "$@"; [ $? -eq 1 ]; }   # grep found nothing; a missing file is an error
export HOME=/tmp
ok 'system name is EvenKeelOS (no dash)' 'grep -qx "NAME=\"EvenKeelOS\"" /usr/lib/os-release && grep -qx "PRETTY_NAME=\"EvenKeelOS\"" /usr/lib/os-release'
ok 'no "EvenKeel-OS" in EvenKeelOS windows' 'none grep -rIl "EvenKeel-OS" /usr/lib/os-release /usr/bin/evenkeel-os-* /usr/share/evenkeel-os /usr/share/applications /etc/xdg/autostart'
ok 'hot corners off' '[ "$(gs org.gnome.desktop.interface enable-hot-corners)" = false ]'
ok 'battery percentage shown' '[ "$(gs org.gnome.desktop.interface show-battery-percentage)" = true ]'
ok 'minimize and maximize buttons' "[ \"\$(gs org.gnome.desktop.wm.preferences button-layout)\" = \"'appmenu:minimize,maximize,close'\" ]"
ok 'no GNOME tour popup' "[ \"\$(gs org.gnome.shell welcome-dialog-last-shown-version)\" = \"'4294967295'\" ]"
ok 'GNOME Tour app removed' '! rpm -q gnome-tour'
ok 'Firefox: no Fedora start page or tile' 'none grep -qi fedoraproject /usr/lib64/firefox/browser/defaults/preferences/firefox-redhat-default-prefs.js'
ok 'Firefox: About says Mozilla Firefox' 'grep -qx "about=Mozilla Firefox" /usr/lib64/firefox/distribution/distribution.ini'
ok 'fastfetch logo is the approved one' '[ "$(sha256sum /usr/share/evenkeel-os/fastfetch-logo.txt | cut -d" " -f1)" = "$LOGO_SUM" ]'
ok 'fastfetch shows the EvenKeelOS logo' 'out=$(fastfetch --pipe false -s OS 2>&1); printf %s "$out" | grep -qF _____________________ && printf %s "$out" | grep -qF EvenKeelOS'
ok 'no Fedora logo package' '! rpm -q fedora-logos'
ok 'automatic rollback (greenboot) on' 'systemctl -q is-enabled greenboot-healthcheck.service && grep -q boot_counter /usr/lib/bootupd/grub2-static/configs.d/08_greenboot.cfg'
ok 'no greenboot check that fails offline' '! rpm -q greenboot-default-health-checks'
for a in $APPS; do ok "default app installed: $a" "rpm -q $a"; done
ok 'Flathub apps listed: Errands, Shortwave, Podcasts, Pika Backup (no Secrets)' '( for i in io.github.mrvladus.List de.haeckerfelix.Shortwave org.gnome.Podcasts org.gnome.World.PikaBackup; do grep -qx $i /usr/share/evenkeel-os/flathub-apps.txt || exit 1; done; ! grep -qi secrets /usr/share/evenkeel-os/flathub-apps.txt )'
ok 'Flathub apps install at first start (service on)' '[ "$(systemctl is-enabled evenkeel-os-flatpak-apps.service)" = enabled ]'
ok 'Flathub apps come from Flathub only (Fedora Flatpak store off)' '[ "$(systemctl is-enabled flatpak-add-fedora-repos.service)" != enabled ]'
ok 'GNOME Software removed' '! rpm -q gnome-software && ! rpm -q gnome-software-rpm-ostree'
ok 'Bazaar in Super search' '[ -f /usr/share/gnome-shell/search-providers/io.github.kolunmi.Bazaar.search-provider.ini ] && [ -f /usr/share/dbus-1/services/io.github.kolunmi.Bazaar.SearchProvider.service ]'
ok 'text files open in Text Editor' '[ "$(XDG_CURRENT_DESKTOP=GNOME gio mime text/plain | head -1 | sed "s/.*: //")" = org.gnome.TextEditor.desktop ]'
ok '.rpm and .deb files open in Install Package File' '[ "$(XDG_CURRENT_DESKTOP=GNOME gio mime application/x-rpm | head -1 | sed "s/.*: //")" = evenkeel-os-install-package.desktop ]'
ok 'Flatpak files open in Bazaar' '[ "$(XDG_CURRENT_DESKTOP=GNOME gio mime application/vnd.flatpak.ref | head -1 | sed "s/.*: //")" = io.github.kolunmi.Bazaar.desktop ]'
ok 'Wheelhouse in the Utilities folder, the other tools inside it' 'dconf read /org/gnome/desktop/app-folders/folders/Utilities/apps | grep -qF evenkeel-os-tools.desktop && ( for a in evenkeel-os-update evenkeel-os-install-package evenkeel-os-remove-apps evenkeel-os-repair-boxes evenkeel-os-login-apps evenkeel-os-codecs; do grep -qx NoDisplay=true /usr/share/applications/$a.desktop || exit 1; done )'
ok 'login screen shows the EvenKeelOS logo' 'gs org.gnome.login-screen logo | grep -qF /usr/share/pixmaps/evenkeel-os-gdm-logo.png && [ -s /usr/share/pixmaps/evenkeel-os-gdm-logo.png ]'
ok 'installed boot-menu entry will be named EvenKeelOS (system-release)' '[ "$(sed "s/ *release.*//" /etc/system-release)" = EvenKeelOS ]'
EOF
)

live_checks=$(cat <<'EOF'
i=/usr/lib/evenkeel-os-installer
e=/usr/libexec/evenkeel-os-install-engine
ok 'system name is EvenKeelOS (no dash)' 'grep -qx "PRETTY_NAME=\"EvenKeelOS\"" /usr/lib/os-release && grep -qxE "EvenKeelOS release [0-9]+" /etc/system-release'
ok 'no Fedora installer (Anaconda) on the USB' '! rpm -q anaconda-core'
ok 'installer launcher: Install EvenKeelOS' 'grep -qx "Name=Install EvenKeelOS" /usr/share/applications/io.github.ctsdownloads.EvenKeelOS.Installer.desktop'
ok 'welcome window: Install EvenKeelOS / Try it first' 'grep -qF "Install EvenKeelOS" /usr/libexec/evenkeel-os-live-welcome && grep -qF "Try it first" /usr/libexec/evenkeel-os-live-welcome && grep -qF /usr/bin/evenkeel-os-installer /usr/libexec/evenkeel-os-live-welcome'
ok 'installer: Alpha badge and EvenKeelOS logo' 'grep -qF "set_text(_(\"Alpha\"))" $i/evenkeel-os-installer && [ -s /usr/share/evenkeel-os-installer/logo-wide.svg ]'
ok 'installer: Desktop layout step with both pictures' 'grep -qF LayoutScreen $i/evenkeel-os-installer && [ -s $i/layout-current.png ] && [ -s $i/layout-windows.png ]'
ok 'installer: problem reports go to GitHub' 'grep -qF github.com/ctsdownloads/EvenKeelOS/issues/new $i/finish_screens.py && command -v qrencode'
ok 'installer: disk changes only through its polkit action' '[ -x $e ] && grep -qF "<annotate key=\"org.freedesktop.policykit.exec.path\">$e<" /usr/share/polkit-1/actions/io.github.ctsdownloads.evenkeel-os.install.policy'
ok 'installer installs EvenKeelOS from the USB, with signed updates' 'grep -qF "IMAGE = \"ghcr.io/ctsdownloads/evenkeel-os:latest\"" $e && grep -qF containers-storage: $e && grep -qF ostree-image-signed:docker:// $e'
ok 'live session does not install Flathub apps' '[ "$(systemctl is-enabled evenkeel-os-flatpak-apps.service)" != enabled ]'
ok 'USB boots Fedora signed shim and grub (Secure Boot on)' 'cd /boot/efi/EFI && cmp -s BOOT/BOOTX64.EFI fedora/shimx64.efi && cmp -s BOOT/fbx64.efi fedora/grubx64.efi && grep -aq "Microsoft Corporation UEFI CA" BOOT/BOOTX64.EFI && grep -aq "Fedora Secure Boot" fedora/grubx64.efi'
ok 'copy to install is on the USB' 'grep -qF ghcr.io/ctsdownloads/evenkeel-os:latest /var/lib/containers/storage/overlay-images/images.json'
EOF
)

out=$(run_in "$sys" "$system_checks" 2>&1)
echo "== The system that gets installed ($sys)"
echo "$out"
fails=$(grep -c '^FAIL' <<<"$out")
[ "$(grep -c '^\(PASS\|FAIL\): ' <<<"$out")" -eq $(($(grep -c '^ok ' <<<"$system_checks") + $(wc -w <<<"$apps"))) ] || { echo "FAIL: not all system checks ran"; fails=$((fails+1)); }
if [ -n "$live" ]; then
  out=$(run_in "$live" "$live_checks" 2>&1)
  echo "== The live USB system and installer ($live)"
  echo "$out"
  fails=$((fails + $(grep -c '^FAIL' <<<"$out")))
  [ "$(grep -c '^\(PASS\|FAIL\): ' <<<"$out")" -eq "$(grep -c '^ok ' <<<"$live_checks")" ] || { echo "FAIL: not all USB checks ran"; fails=$((fails+1)); }
  # The copy on the USB must be the system checked above.
  id=$(sudo podman image inspect "$sys" --format '{{.Id}}')
  if run_in "$live" "grep -qF $id /var/lib/containers/storage/overlay-images/images.json" >/dev/null 2>&1; then
    echo "PASS: the copy on the USB is exactly the system checked above"
  else
    echo "FAIL: the copy on the USB is not the system checked above"; fails=$((fails+1))
  fi
fi
if [ "$fails" -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "$fails CHECK(S) FAILED"; exit 1; fi
