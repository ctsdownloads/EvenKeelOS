#!/usr/bin/bash
# Build a test ISO locally. Run from a normal terminal; needs sudo and about 70 GB free.
set -euo pipefail
trap 'echo; echo "STOPPED at: $BASH_COMMAND"' ERR

if [ -e /run/.containerenv ] || [ -n "${CONTAINER_ID:-}" ]; then
  echo "This terminal is inside a container (toolbox or distrobox). Run this in a normal terminal."; exit 1
fi
cd "$(dirname "$0")/.."
free=$(df --output=avail -BG . | tail -1 | tr -dc 0-9)
[ "$free" -ge 70 ] || { echo "Only ${free} GB free here. It needs 70 GB."; exit 1; }

out="$HOME/Downloads/evenkeel-os-iso"
payload=iso/src/payload.oci.tar

# Keep sudo alive for the whole build.
sudo -v
while true; do sudo -n true; sleep 50; done 2>/dev/null &
keepalive=$!
trap 'kill $keepalive 2>/dev/null; sudo rm -f "$payload"' EXIT

# Step 1 is skipped when its files are unchanged; sudo podman rmi localhost/evenkeel-os to force it.
stamp="$HOME/.cache/evenkeel-os-local-image-v2"   # v2: images built before --no-cache are not trusted
src=$(git ls-files -s Containerfile build_files system_files | sha256sum | cut -c1-16)
git diff --quiet HEAD -- Containerfile build_files system_files || src="changed-$(date +%s)"
if [ "$(cat "$stamp" 2>/dev/null)" = "$src" ] && sudo podman image exists localhost/evenkeel-os; then
  echo "== 1 of 3: the EvenKeelOS image: unchanged since the last build here, using that one"
else
  rm -f "$stamp"
  echo "== 1 of 3: the EvenKeelOS image"
  # No cache: podman misses changed build files.
  sudo podman build --no-cache -t localhost/evenkeel-os -f Containerfile .
  # Small layers, as on GitHub, or the install runs out of memory.
  sudo build_files/rechunk.sh evenkeel-os latest
  sudo podman image prune -f >/dev/null      # the unsplit copy
  mkdir -p "$(dirname "$stamp")" && echo "$src" > "$stamp"
fi
layers=$(sudo podman image inspect localhost/evenkeel-os --format '{{len .RootFS.Layers}}')
[ "$layers" -ge 20 ] || { echo "The EvenKeelOS image has only $layers layers; it was not split. Stopping."; exit 1; }
# The image must come from the files in this folder.
want=$(sed -n 's/^PRETTY_NAME="\(.*\)"$/\1/p' build_files/rebrand.sh)
got=$(sudo podman run --rm --pull=never --entrypoint /usr/bin/sh localhost/evenkeel-os -c '. /usr/lib/os-release; echo "$PRETTY_NAME"; cat /etc/dconf/db/distro.d/50-evenkeel-os-app-folders >/dev/null && echo folders-ok')
[ "$got" = "$want
folders-ok" ] || { echo "The EvenKeelOS image is not built from this folder (it says: $got). Stopping."; exit 1; }
echo "image checked: built from this folder ($want)"

echo "== 2 of 3: the live variant, with that image as the copy to install"
sudo rm -f "$payload"
sudo podman save --format oci-archive -o "$payload" localhost/evenkeel-os
sudo podman build --no-cache --cap-add sys_admin --security-opt label=disable --squash \
  --build-arg BASE_IMAGE=localhost/evenkeel-os -t localhost/evenkeel-os-live -f iso/Containerfile .
sudo rm -f "$payload"

echo "== Checking every change inside the built system and the USB system"
iso/verify-image.sh localhost/evenkeel-os localhost/evenkeel-os-live

echo "== 3 of 3: the ISO"
# titanoboa at the commit locked in build_files/locked-versions.txt.
tb=$(awk '$1 == "git" && $2 == "ublue-os/titanoboa" {print $4}' build_files/locked-versions.txt)
[[ $tb =~ ^[0-9a-f]{40}$ ]] || { echo "No titanoboa commit in build_files/locked-versions.txt. Stopping."; exit 1; }
[ -d "$HOME/titanoboa" ] || git clone --quiet https://github.com/ublue-os/titanoboa.git "$HOME/titanoboa"
git -C "$HOME/titanoboa" fetch --quiet origin "$tb"
git -C "$HOME/titanoboa" checkout --quiet --detach "$tb"
mkdir -p "$out"
(cd "$HOME/titanoboa" && sudo TITANOBOA_CTR_IMAGE=localhost/evenkeel-os-live TITANOBOA_OUTPUT_DIR="$out" ./main.sh)
ls -lh "$out"
echo "Done. Write the .iso above to a USB stick with GNOME Disks (Restore Disk Image) or Fedora Media Writer."
