#!/usr/bin/bash
# Lock screen: the password box's outline in the accent color, as on the login screen (GNOME draws it white there).
# Adds one rule to GNOME Shell's own style file, rebuilt from Fedora's current copy every build; nothing else changes.
set -euo pipefail
G=/usr/share/gnome-shell/gnome-shell-theme.gresource
d=$(mktemp -d)
rule='.unlock-dialog .login-dialog-prompt-entry:focus { box-shadow: inset 0 0 0 2px st-transparentize(st-mix(-st-accent-color, #ffffff, 60%), 0.2) !important; }'
xml="<?xml version=\"1.0\" encoding=\"UTF-8\"?><gresources><gresource prefix=\"/\">"
for r in $(gresource list "$G"); do
  mkdir -p "$d$(dirname "$r")"
  gresource extract "$G" "$r" >"$d$r"
  xml+="<file>${r#/}</file>"
done
for v in dark light; do
  css=$d/org/gnome/shell/theme/gnome-shell-$v.css
  # GNOME's own lock screen rule must still exist, so ours overrides the right thing.
  grep -q '^  \.unlock-dialog \.login-dialog-prompt-entry:focus {' "$css" \
    || { echo "ERROR: GNOME's lock screen password box rule is gone from gnome-shell-$v.css; update $0"; exit 1; }
  printf '\n/* EvenKeelOS: lock screen password box in the accent color */\n%s\n' "$rule" >>"$css"
done
xml+="</gresource></gresources>"
printf '%s\n' "$xml" >"$d/theme.gresource.xml"
glib-compile-resources --sourcedir="$d" --target="$G" "$d/theme.gresource.xml"
for v in dark light; do
  gresource extract "$G" "/org/gnome/shell/theme/gnome-shell-$v.css" | grep -qF "$rule" \
    || { echo "ERROR: the lock screen rule is not in GNOME Shell's gnome-shell-$v.css"; exit 1; }
done
[ "$(gresource list "$G" | wc -l)" -ge "$(grep -o '<file>' "$d/theme.gresource.xml" | wc -l)" ] \
  || { echo "ERROR: GNOME Shell's style file lost parts when rebuilt"; exit 1; }
rm -rf "$d"
echo "Lock screen: password box outline follows the accent color"
