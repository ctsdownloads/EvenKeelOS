#!/bin/bash
# Daily version check: writes the newest versions into locked-versions.txt; run from the repo root with NOTES-FILE.
set -euo pipefail

lock=build_files/locked-versions.txt
notes=$1
fedora=$(sed -n 's|^FROM quay.io/fedora-ostree-desktops/silverblue:\([0-9][0-9]*\)$|\1|p' Containerfile)
[ -n "$fedora" ] || { echo "ERROR: no Fedora version found in the Containerfile"; exit 1; }

# Newest version of each locked package, asked from Copr by Fedora's own package tool.
declare -A newest
mapfile -t projects < <(awk '$1 == "copr" {print $2}' "$lock" | sort -u)
for project in "${projects[@]}"; do
  mapfile -t names < <(awk -v p="$project" '$1 == "copr" && $2 == p {print $3}' "$lock")
  url="https://download.copr.fedorainfracloud.org/results/$project/fedora-$fedora-x86_64/"
  found=$(docker run --rm "quay.io/fedora/fedora:$fedora" dnf5 -q repoquery --disablerepo='*' \
    --repofrompath="copr,$url" --enablerepo=copr --latest-limit=1 --arch=x86_64,noarch \
    --qf '%{name} %{version}-%{release}\n' "${names[@]}")
  while read -r name version; do
    [ -n "$name" ] && newest[$name]=$version
  done <<< "$found"
done

# Newest Fedora version of each locked Fedora package, and the GNOME version extensions must support.
mapfile -t fedora_names < <(awk '$1 == "fedora" {print $3}' "$lock")
found=$(docker run --rm "quay.io/fedora/fedora:$fedora" dnf5 -q repoquery --latest-limit=1 --arch=x86_64,noarch \
  --qf '%{name} %{version}-%{release}\n' gnome-shell "${fedora_names[@]}")
while read -r name version; do
  [ -n "$name" ] && newest[$name]=$version
done <<< "$found"
gnome=${newest[gnome-shell]%%.*}

: > "$notes"
new_lock=$(mktemp)
while IFS= read -r line; do
  read -r kind source name version _ <<< "$line" || true
  case $kind in
    copr) new=${newest[$name]:-}; label=$name; link="https://copr.fedorainfracloud.org/coprs/$source/package/$name/" ;;
    fedora) new=${newest[$name]:-}; label=$name
            link="https://koji.fedoraproject.org/koji/packageinfo?packageID=$name" ;;
    gnome-extension)
      # source is the extension's uuid, name its version on extensions.gnome.org, version its sha256
      ego=https://extensions.gnome.org; label=$source; link="$ego/extension-info/?uuid=$source"
      latest=$(curl -fsSL "$ego/extension-info/?uuid=$source&shell_version=$gnome" | jq -r .version)
      [[ $latest =~ ^[0-9]+$ ]] \
        || { echo "ERROR: extensions.gnome.org gave $source an unexpected version: $latest"; exit 1; }
      if [ "$latest" != "$name" ]; then
        sha=$(curl -fsSL "$ego/extension-data/${source//@/}.v$latest.shell-extension.zip" | sha256sum)
        echo "- **$label**: version $name to $latest, $link" >> "$notes"
        line="$kind $source $latest ${sha%% *}"
      fi
      printf '%s\n' "$line" >> "$new_lock"; continue ;;
    git) ref="refs/heads/$name"; label=${source#*/}
         new=$(git ls-remote "https://github.com/$source" "$ref" | awk -v r="$ref" '$2 == r {print $1}')
         link="https://github.com/$source/compare/$version...$new" ;;
    *) printf '%s\n' "$line" >> "$new_lock"; continue ;;
  esac
  [ -n "$new" ] || { echo "ERROR: no version of $label found in $source"; exit 1; }
  if [ "$kind" = git ]; then format='^[0-9a-f]{40}$'; else format='^[A-Za-z0-9._+~^]+-[A-Za-z0-9._+~^]+$'; fi
  [[ $new =~ $format ]] || { echo "ERROR: $source gave $label an unexpected version: $new"; exit 1; }
  if [ "$new" != "$version" ]; then
    echo "- **$label** ($source): $version to $new, $link" >> "$notes"
    line="$kind $source $name $new"
  fi
  printf '%s\n' "$line" >> "$new_lock"
done < "$lock"
mv "$new_lock" "$lock"
if [ -s "$notes" ]; then cat "$notes"; else echo "Everything is at the newest version"; fi
