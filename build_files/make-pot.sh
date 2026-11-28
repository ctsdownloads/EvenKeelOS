#!/usr/bin/bash
# Collects every line people see into po/evenkeel-os.pot for translators; --check fails if that file is out of date.
set -euo pipefail
cd "$(dirname "$0")/.."
export GETTEXTDATADIRS=$PWD/po     # po/its: which parts of a .policy file are text
pot=po/evenkeel-os.pot
new=$(mktemp)
trap 'rm -f "$new"' EXIT

py=() sh=()
for f in build_files/*.py build_files/evenkeel_os_packages/*.py build_files/evenkeel-os-* build_files/greenboot/* \
         iso/src/evenkeel-os-* iso/src/evenkeel-os-installer/*.py \
         iso/src/evenkeel-os-installer/evenkeel-os-installer; do
  [ -f "$f" ] || continue
  case "$f" in build_files/check-*|build_files/make-*) continue ;; esac
  case "$(head -1 "$f")" in
    *python*) py+=("$f") ;;
    *bash*|*/sh) sh+=("$f") ;;
    *) [[ $f == *.py ]] && py+=("$f"); [[ $f == *.sh ]] && sh+=("$f") ;;
  esac
done
other=(build_files/*.desktop iso/src/*.desktop build_files/*.policy iso/src/*.policy)

common=(--from-code=UTF-8 --package-name=EvenKeelOS
        --msgid-bugs-address=https://github.com/ctsdownloads/EvenKeelOS/issues
        --add-comments=Translators: --sort-by-file --no-location -o "$new")
xgettext "${common[@]}" -L Python -k_ -kN_ -k_dates -kngettext:1,2 "${py[@]}"
xgettext "${common[@]}" -j -L Shell -k -kgettext "${sh[@]}"
xgettext "${common[@]}" -j "${other[@]}"
# What each Windows program does ("job"), shown in the Windows Program window.
jq -r '[(.programs, .kinds)[].job | select(.)] | unique[] | "_(\(@json))"' build_files/windows-replacements.json \
  | xgettext "${common[@]}" -j -L Python -
# Each change's title, shown under "What is new" in System Update (one per line; every PR adds its own).
jq -R -r '"# Translators: a change in an update, listed under What is new\n_(\(tojson))"' po/whats-new.txt \
  | xgettext "${common[@]}" -j -L Python -

if [ "${1:-}" = --check ]; then
  same() { grep -v '^"POT-Creation-Date:' "$1"; }
  diff <(same "$pot") <(same "$new") >/dev/null \
    || { echo "ERROR: po/evenkeel-os.pot is out of date: run build_files/make-pot.sh"; exit 1; }
else
  cp "$new" "$pot"
fi
