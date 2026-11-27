#!/bin/bash
# The outside apps' text at their locked versions is the text we translated (po/apps/APP.pot), and every
# translation file is valid. Fails when a newer locked version brings new text: translate it, see
# docs/building.md#translations. Needs curl, jq, rpm2cpio, cpio and gettext. Run from the repository root.
set -euo pipefail
export LC_ALL=C.UTF-8
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
# Every msgid, context and plural, whole (multi-line ones too); the header block, first when sorted, aside.
lines() { msgcat --no-location --sort-output --no-wrap "$1" | grep -v '^#' | awk -v RS= 'NR > 1'; }
for app in dash-to-panel arcmenu logo-menu bazaar ghostty; do
  build_files/app-texts.sh "$app" "$work/$app.pot"
  diff <(lines "po/apps/$app.pot") <(lines "$work/$app.pot") >/dev/null \
    || { echo "ERROR: $app's locked version has new text. Translate it: docs/building.md#translations"; exit 1; }
done
for f in po/apps/*/*.po; do msgfmt -c -o /dev/null "$f"; done
echo "Dash to Panel, ArcMenu, Logo Menu, Bazaar and Ghostty: the text we translated is the text of the locked versions"
