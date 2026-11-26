#!/bin/bash
# Every language in po/LINGUAS has a complete, valid translation of po/evenkeel-os.pot.
set -euo pipefail
cd "$(dirname "$0")/.."
listed=$(sort po/LINGUAS)
files=$(for f in po/*.po; do basename "$f" .po; done | sort)
[ "$listed" = "$files" ] || { echo "ERROR: po/LINGUAS and the .po files don't match"; diff <(echo "$listed") <(echo "$files"); exit 1; }
for lang in $listed; do
  po=po/$lang.po
  msgfmt -c -o /dev/null "$po"
  msgcmp "$po" po/evenkeel-os.pot
  [ -z "$(msgattrib --only-fuzzy --no-obsolete "$po")" ] || { echo "ERROR: $po has lines marked fuzzy"; exit 1; }
  [ -z "$(msgattrib --untranslated --no-obsolete "$po")" ] || { echo "ERROR: $po has untranslated lines"; exit 1; }
done
echo "All $(grep -c . po/LINGUAS) languages are complete."
