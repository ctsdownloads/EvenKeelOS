#!/usr/bin/bash
# Build check: a teal default, a colored icon set per GNOME accent color, and the helper picks the right one.
set -euo pipefail
fail() { echo "ERROR: $*"; exit 1; }
got=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.desktop.interface icon-theme)
[ "$got" = "'Adwaita-teal'" ] || fail "the default icons are $got, not Adwaita-teal"
declare -A hex=([teal]=129eb0 [green]=3d9e4f [yellow]=cb931a [orange]=f17738 [red]=e84053 [pink]=e64392
                [purple]=954ab5 [slate]=637692)
[ -f /usr/share/icons/Adwaita-blue/index.theme ] || fail "Adwaita-blue (the colored sets build on it) is missing"
for c in "${!hex[@]}"; do
  f=/usr/share/icons/Adwaita-$c/scalable/places/folder.svg
  grep -qi "${hex[$c]}" "$f" || fail "$f is missing or not in its color"
  grep -qx 'Inherits=Adwaita,Adwaita-blue,AdwaitaLegacy,hicolor' "/usr/share/icons/Adwaita-$c/index.theme" \
    || fail "Adwaita-$c doesn't fall back to GNOME's own icons"
done
# Every color Settings offers has its set (blue is GNOME's own).
for c in $(sed -n '/id="org.gnome.desktop.GDesktopAccentColor"/,/<\/enum>/s/.*nick="\([a-z]*\)".*/\1/p' \
             /usr/share/glib-2.0/schemas/org.gnome.desktop.enums.xml); do
  [ "$c" = blue ] || [ -n "${hex[$c]:-}" ] || fail "Settings offers the accent color $c, which has no folder icons"
done
# The helper, against a throwaway settings file.
export XDG_CONFIG_HOME GSETTINGS_BACKEND=keyfile
XDG_CONFIG_HOME=$(mktemp -d)
s() { gsettings set org.gnome.desktop.interface "$1" "$2"; }
g() { gsettings get org.gnome.desktop.interface icon-theme | tr -d "'"; }
h=/usr/libexec/evenkeel-os-accent-icons
s accent-color teal; "$h" --once; [ "$(g)" = Adwaita-teal ] || fail "the helper changed the teal default to $(g)"
s accent-color purple; "$h" --once; [ "$(g)" = Adwaita-purple ] || fail "purple accent gave $(g)"
s accent-color blue; "$h" --once; [ "$(g)" = Adwaita ] || fail "blue accent gave $(g), not GNOME's own icons"
s icon-theme Papirus; s accent-color red; "$h" --once; [ "$(g)" = Papirus ] || fail "the helper replaced another icon theme"
rm -rf "$XDG_CONFIG_HOME"
echo "Folder icons: teal by default, a set per accent color, the helper follows the accent and leaves other themes alone"
