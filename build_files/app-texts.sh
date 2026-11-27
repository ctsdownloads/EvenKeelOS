#!/bin/bash
# An outside app's text at its locked version, as a template; from the repo root: app-texts.sh APP OUT.pot
set -euo pipefail
export LC_ALL=C.UTF-8
app=$1 out=$2
lock=build_files/locked-versions.txt
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
field() { awk -v k="$1" -v n="$2" '$1 == k && ($2 == n || $3 == n) {print $3, $4}' "$lock"; }
js() { xgettext --no-location -k_ -kN_ -kngettext:1,2 -kpgettext:1c,2 --from-code=UTF-8 -o "$out" "$@"; }
case $app in
  dash-to-panel)
    read -r _ version < <(field fedora gnome-shell-extension-dash-to-panel)
    curl -fsSL -o "$work/p.rpm" "https://kojipkgs.fedoraproject.org/packages/gnome-shell-extension-dash-to-panel/\
${version%-*}/${version##*-}/noarch/gnome-shell-extension-dash-to-panel-$version.noarch.rpm"
    (cd "$work" && rpm2cpio p.rpm | cpio -idm --quiet)
    mapfile -t files < <(find "$work"/usr/share/gnome-shell/extensions -name '*.js' -o -name '*.ui' | sort)
    js "${files[@]}" ;;
  arcmenu | logo-menu)
    uuid=$([ "$app" = arcmenu ] && echo arcmenu@arcmenu.com || echo logomenu@aryan_k)
    read -r version sha < <(field gnome-extension "$uuid")
    curl -fsSL -o "$work/e.zip" "https://extensions.gnome.org/extension-data/${uuid//@/}.v$version.shell-extension.zip"
    echo "$sha  $work/e.zip" | sha256sum -c --quiet -
    python3 -I -m zipfile -e "$work/e.zip" "$work/e"
    mapfile -t files < <(find "$work/e" -name '*.js' | sort)
    js -L JavaScript "${files[@]}" ;;
  bazaar)
    read -r _ version < <(field copr bazaar)
    srpm=$(curl -fsSL "https://copr.fedorainfracloud.org/api_3/build/list/?ownername=ublue-os&projectname=packages\
&packagename=bazaar&limit=100" | jq -r --arg v "$version" \
      '[.items[] | select(.source_package.version == ($v | sub("\\.fc[0-9]+$"; "")))][0].source_package.url')
    curl -fsSL -o "$work/s.rpm" "$srpm"
    (cd "$work" && rpm2cpio s.rpm | cpio -idm --quiet && tar xzf ./*.tar.gz)
    src=$(dirname "$(find "$work" -path '*/po/POTFILES.in')")/..
    grep -v '^#' "$src/po/POTFILES.in" | grep . > "$work/files"
    # Bazaar uses "Install" both with and without a plural: xgettext reports it, still writes the list, and exits 1.
    (cd "$src" && xgettext --no-location --from-code=UTF-8 --add-comments -k_ -kN_ -kC_:1c,2 -kNC_:1c,2 \
      -kngettext:1,2 -kg_ngettext:1,2 -kg_dngettext:2,3 -kg_dpgettext2:2c,3 -kQ_ -kg_dcgettext:2 \
      -o "$out" -f "$work/files") || [ -s "$out" ]
    # Keep that line once, without the plural, as Bazaar's own translations have it.
    awk -v RS= -v ORS='\n\n' '!/(^|\n)msgid "Install"\nmsgid_plural "Installs"/' "$out" > "$work/p"
    mv "$work/p" "$out" ;;
  ghostty)
    read -r _ version < <(field copr ghostty)
    base=https://download.copr.fedorainfracloud.org/results/scottames/ghostty/fedora-$(sed -n \
      's|^FROM quay.io/fedora-ostree-desktops/silverblue:\([0-9]*\)$|\1|p' Containerfile)-x86_64
    curl -fsSL -o "$work/s.rpm" "$base/Packages/g/ghostty-$version.src.rpm"
    (cd "$work" && rpm2cpio s.rpm | cpio -idm --quiet && tar xzf ./*.tar.gz --wildcards '*/po/*.pot')
    cp "$(find "$work" -name '*.pot')" "$out" ;;
  *) echo "ERROR: unknown app $app"; exit 1 ;;
esac
sed -i 's/charset=CHARSET/charset=UTF-8/' "$out"
