#!/usr/bin/bash
# Downloads what Windows Program's list and tests need into DIR. A file that can't be downloaded keeps the copy
# already in DIR (saved from the last build), so one site being down doesn't stop the build.
set -euo pipefail
dir=$1
mkdir -p "$dir"

get() {
  local url=$1 name=$2
  if curl -fsSL --retry 3 -o "$dir/$name.new" "$url"; then
    mv "$dir/$name.new" "$dir/$name"
  elif [ -s "$dir/$name" ]; then
    rm -f "$dir/$name.new"
    echo "Using the saved copy of $name: $url can't be reached"
  else
    echo "ERROR: $url can't be reached and there is no saved copy"
    exit 1
  fi
}

get https://cdn.winget.microsoft.com/cache/source.msix source.msix
get https://dl.flathub.org/repo/appstream/x86_64/appstream.xml.gz flathub.xml.gz
# Ubuntu's lists are for the Ubuntu box's version (24.04).
for c in main universe; do
  get "https://archive.ubuntu.com/ubuntu/dists/noble/$c/dep11/Components-amd64.yml.gz" "ubuntu-$c.yml.gz"
done

# Five real installers, pinned by checksum, to test reading .exe and .msi files; a good saved copy is kept.
sums='9b697f65ecc2d9b0152f5ee96d72dde522a7827690349d9307935dacf40f42ec  7z2606-x64.exe
ce3267f5c4e7e42f847e00f4b20234da6150647203033cdde34a69593efc3152  npp.8.9.9.1.Installer.x64.exe
2213ebacf962b709411d654a40087508a694756bc4e41c5a1c24ad86596b2511  putty-64bit-0.85-installer.msi
c8e7ee33b43b9fd6baada11b4355a684bb8944ea58173423fa108d244bcbdf0a  bit-Bitwarden-Installer-2026.11.0.exe
8956c0614fcea863730559109e9787ccce37034d72a7faf954945361e58ec48d  qutebrowser-3.7.0-amd64.exe'
while read -r url; do
  name=${url##*/}
  (cd "$dir" && grep -F "  $name" <<<"$sums" | sha256sum -c --quiet --status 2>/dev/null) || get "$url" "$name"
done <<'URLS'
https://www.7-zip.org/a/7z2606-x64.exe
https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.9.9.1/npp.8.9.9.1.Installer.x64.exe
https://the.earth.li/~sgtatham/putty/0.85/w64/putty-64bit-0.85-installer.msi
https://github.com/bitwarden/clients/releases/download/desktop-v2026.11.0/bit-Bitwarden-Installer-2026.11.0.exe
https://github.com/qutebrowser/qutebrowser/releases/download/v3.7.0/qutebrowser-3.7.0-amd64.exe
URLS
(cd "$dir" && sha256sum -c --quiet <<<"$sums") \
  || { echo "ERROR: a test installer for Windows Program has changed"; exit 1; }
