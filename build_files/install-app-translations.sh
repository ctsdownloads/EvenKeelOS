#!/bin/bash
# Installs outside apps' translations, filling gaps from po/apps/APP/LANG.po; fails on any missing line. Usage: PO-DIR
set -euo pipefail
export LC_ALL=C.UTF-8
po=$1
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
ext=/usr/share/gnome-shell/extensions
#      app           gettext domain           where its translations live
apps=("dash-to-panel dash-to-panel           /usr/share/locale"
      "arcmenu       arcmenu                 $ext/arcmenu@arcmenu.com/locale"
      "logo-menu     logo-menu               $ext/logomenu@aryan_k/locale"
      "bazaar        bazaar                  /usr/share/locale"
      "ghostty       com.mitchellh.ghostty   /usr/share/locale")

maker() {     # the maker's translation for a language, else a regional one ("es" from "es_ES"), else nothing
  local dir=$1 domain=$2 lang=$3 f
  for f in "$dir/$lang" "$dir/${lang}_${lang^^}" "$dir/${lang}_"*; do
    # A region that is a language of its own here (pt_BR for pt) is not used for another.
    [ "$f" = "$dir/$lang" ] || ! grep -qx "${f##*/}" "$po/LINGUAS" || continue
    [ -f "$f/LC_MESSAGES/$domain.mo" ] && { echo "$f/LC_MESSAGES/$domain.mo"; return 0; }
  done
  return 0
}
# Which plural form a file picks for the numbers 0 to 999, read from its Plural-Forms rule.
plurals() {
  python3 -I -c 'import gettext, re, sys
rule = re.search(r"plural=([^;\\\"]*)", open(sys.argv[1], encoding="utf-8").read().replace("\"\n\"", ""))
print(" ".join(str(gettext.c2py(rule.group(1))(n)) for n in range(1000)) if rule else "none")' "$1"
}

for row in "${apps[@]}"; do
  read -r app domain dir <<< "$row"
  pot=$po/apps/$app.pot
  while read -r lang; do
    case $lang in en_GB) continue ;; de_CH) from=de ;; bn_IN) from=bn ;; *) from=$lang ;; esac
    out=$work/$app-$lang.po
    ours=$po/apps/$app/$from.po
    [ -f "$ours" ] || ours=/dev/null
    m=$(maker "$dir" "$domain" "$from")
    if [ -n "$m" ]; then
      # The maker's lines that match this version's text exactly, then ours for the rest, under our header.
      msgunfmt -o "$work/maker.po" "$m"
      msgmerge -q --no-fuzzy-matching -o "$work/kept.po" "$work/maker.po" "$pot"
      msgattrib --no-fuzzy --no-obsolete --translated -o "$work/kept.po" "$work/kept.po"
      # A maker whose plural rule picks forms differently would show the wrong word: its plural lines are dropped.
      if [ "$(plurals "$work/maker.po")" != "$(plurals "$po/$from.po")" ]; then
        awk -v RS= -v ORS='\n\n' '!/\nmsgid_plural /' "$work/kept.po" > "$work/kept1.po"
        mv "$work/kept1.po" "$work/kept.po"
      fi
      msggrep -K -E -e '^$' -o "$work/header.po" "$po/$from.po"
      msgcat --use-first -o "$work/all.po" "$work/header.po" "$work/kept.po" "$ours"
    else
      [ "$ours" != /dev/null ] || { echo "ERROR: $app has no translation in $lang"; exit 1; }
      cp "$ours" "$work/all.po"
    fi
    msgmerge -q --no-fuzzy-matching -o "$out" "$work/all.po" "$pot"
    [ "$lang" = de_CH ] && sed -i '/^msgstr/,/^$/ s/ß/ss/g' "$out"
    # msgfmt's last line is the count ("N translated messages."); warnings before it stay in the error.
    stats=$(msgfmt -c --statistics -o "$work/out.mo" "$out" 2>&1) || stats+=$'\nfailed'
    [[ ${stats##*$'\n'} =~ ^[0-9]+\ translated\ messages?\.$ ]] || { echo "ERROR: $app in $lang: $stats"; exit 1; }
    install -Dm644 "$work/out.mo" "$dir/$lang/LC_MESSAGES/$domain.mo"
  done < "$po/LINGUAS"
done
echo "Dash to Panel, ArcMenu, Logo Menu, Bazaar and Ghostty are complete in every language of po/LINGUAS"
