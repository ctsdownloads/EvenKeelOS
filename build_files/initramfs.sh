#!/usr/bin/bash
# Rebuild the initramfs with the EvenKeelOS logo; fail if anything needed to boot or unlock is missing.
set -euo pipefail

kvers=(/usr/lib/modules/*/)
[ "${#kvers[@]}" -eq 1 ] || { echo "ERROR: expected exactly one kernel, found ${#kvers[@]}"; exit 1; }
KVER=$(basename "${kvers[0]}")
IMG=/usr/lib/modules/$KVER/initramfs.img
# A kernel updated during the build has no initramfs yet.
if [ -f "$IMG" ]; then mode=$(stat -c %a "$IMG"); else mode=600; echo "no initramfs yet for $KVER (kernel updated during the build), making one"; fi

# Blank logos instead of generic-logos' mascot.
python3 - <<'PY'
import zlib, struct
def chunk(t, d):
    c = struct.pack('>I', len(d)) + t + d
    return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
def blank(path, w, h):
    raw = b''.join(b'\x00' + b'\x00' * (w * 4) for _ in range(h))
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    open(path, 'wb').write(png)
blank('/usr/share/pixmaps/system-logo-white.png', 240, 310)
blank('/usr/share/pixmaps/fedora-logo.png', 240, 310)
blank('/usr/share/pixmaps/fedora-logo-small.png', 128, 128)
PY
# EvenKeelOS logo at the bottom of the boot and unlock screens.
install -Dm644 /ctx/branding/boot-watermark.png /usr/share/plymouth/themes/spinner/watermark.png

export DRACUT_NO_XATTR=1
mkdir -p /tmp/dracut
dracut --reproducible -v --add ostree --tmpdir /tmp/dracut -f --no-hostonly --kver "$KVER" "$IMG"
chmod "$mode" "$IMG"

# Everything needed to unlock an encrypted disk and boot.
mods=$(lsinitrd -m "$IMG")
for m in ostree crypt plymouth dm lvm systemd-cryptsetup kernel-modules tpm2-tss; do
  grep -qx "$m" <<< "$mods" || { echo "ERROR: the new initramfs lacks dracut module: $m"; exit 1; }
done

# The splash artwork must be the EvenKeelOS logo.
WM=usr/share/plymouth/themes/spinner/watermark.png
want=$(sha256sum /ctx/branding/boot-watermark.png | cut -d' ' -f1)
listing=$(lsinitrd "$IMG")
if ! grep -qE " ${WM}\$" <<< "$listing"; then
  echo "ERROR: $WM is missing from the new initramfs"; exit 1
fi
got=$(lsinitrd "$IMG" -f "$WM" | sha256sum | cut -d' ' -f1)
[ "$want" = "$got" ] || { echo "ERROR: the splash artwork inside the new initramfs is not the EvenKeelOS logo (expected ${want:0:12}, found ${got:0:12})"; exit 1; }
echo "initramfs rebuilt for $KVER: $(du -h "$IMG" | cut -f1), modules ok, EvenKeelOS logo in place"
