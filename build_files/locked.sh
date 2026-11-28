# shellcheck shell=bash
# Reads locked-versions.txt; sourced by build.sh and app-texts.sh with its path.
LOCKED=$1

locked() {        # $1: kind, $2: source or name; each matching line's fields 3 and 4
  awk -v k="$1" -v n="$2" '$1 == k && ($2 == n || $3 == n) {print $3, $4}' "$LOCKED"
}

extension_zip() { # $1: uuid, $2: folder; extensions.gnome.org's zip at its locked version, sha256-checked, unpacked
  local version sha zip
  read -r version sha < <(locked gnome-extension "$1")
  zip=$(mktemp)
  curl -fsSL --retry 3 -o "$zip" "https://extensions.gnome.org/extension-data/${1//@/}.v$version.shell-extension.zip"
  echo "$sha  $zip" | sha256sum -c --quiet -
  python3 -I -m zipfile -e "$zip" "$2"
  rm "$zip"
}
