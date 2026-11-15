#!/bin/bash
# Swap Fedora's branding for generic packages (Fedora trademark rules); fails on anything wrong.
set -euo pipefail

fedora=$(rpm -E %fedora)
plan=$(dnf5 install --assumeno --allowerasing generic-logos generic-release 2>&1 || true)
# dnf5 shows removals as "Removing ..." or "replacing NAME".
removed=$(printf '%s\n' "$plan" | awk '
/^Removing[A-Za-z ]*:$/ {rm=1; next}
/^[A-Z][A-Za-z ]*:$/ {rm=0}
rm && NF {print $1; next}
/^[[:space:]]+replacing[[:space:]]/ {print $2}')
if [ -z "$removed" ]; then
  echo "ERROR: the rebranding plan removes nothing. Did dnf's output change?"; printf '%s\n' "$plan" | tail -20; exit 1
fi
bad=$(printf '%s\n' "$removed" | grep -vE '^(fedora-logos|fedora-release(-[a-z0-9-]+)?)$' || true)
if [ -n "$bad" ]; then echo "ERROR: rebranding would also remove: $(echo $bad)"; exit 1; fi

# Keep Fedora's service presets: copy out the ones fedora-release packages own.
presets=$(ls /usr/lib/systemd/system-preset/*.preset /usr/lib/systemd/user-preset/*.preset)
grep -qx /usr/lib/systemd/system-preset/90-default.preset <<<"$presets" || { echo "ERROR: Fedora's preset files were not found"; exit 1; }
keep=$(mktemp -d)
for f in $presets; do
  rpm -qf --qf '%{NAME}\n' "$f" 2>/dev/null | grep -q '^fedora-release' || continue
  mkdir -p "$keep$(dirname "$f")"; cp -a "$f" "$keep$f"
done

dnf5 -y install --allowerasing generic-logos generic-release
rpm -q generic-logos generic-release
if rpm -q fedora-logos fedora-release-common >/dev/null 2>&1; then echo "ERROR: Fedora branding packages are still installed"; exit 1; fi

# Put them back as NN-name-fedora.preset, which sorts first.
for f in $(cd "$keep" && find usr -name '*.preset'); do
  install -Dm644 "$keep/$f" "/$(dirname "$f")/$(basename "$f" .preset)-fedora.preset"
done
rm -rf "$keep"
for f in $presets; do
  [ -f "$f" ] || [ -f "${f%.preset}-fedora.preset" ] || { echo "ERROR: rebranding lost $f"; exit 1; }
done

# The image's own name; ID_LIKE keeps Fedora-family tools working.
cat > /usr/lib/os-release <<OSREL
NAME="EvenKeelOS"
ID=evenkeel-os
ID_LIKE="fedora"
VERSION_ID=$fedora
VERSION="$fedora"
PLATFORM_ID="platform:f$fedora"
PRETTY_NAME="EvenKeelOS"
ANSI_COLOR="0;36"
HOME_URL="https://github.com/ctsdownloads/evenkeel-os"
DOCUMENTATION_URL="https://github.com/ctsdownloads/evenkeel-os"
SUPPORT_URL="https://github.com/ctsdownloads/evenkeel-os/issues"
BUG_REPORT_URL="https://github.com/ctsdownloads/evenkeel-os/issues"
OSREL
ln -sf ../usr/lib/os-release /etc/os-release
# The boot menu entry is named from /etc/system-release.
printf 'EvenKeelOS release %s\n' "$fedora" > /usr/lib/fedora-release
[ "$(sed 's/ *release.*//' /etc/system-release)" = EvenKeelOS ] || { echo "ERROR: /etc/system-release does not name EvenKeelOS"; exit 1; }
echo "rebranded: $(. /usr/lib/os-release; echo "$PRETTY_NAME")"
