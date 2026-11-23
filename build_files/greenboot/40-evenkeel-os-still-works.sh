#!/usr/bin/bash
# On trial, after a login (30 runs first): what worked at the last good start must still work (evenkeel_os_health).
vars=$(grub2-editenv /boot/grub2/grubenv list)
# greenboot names the version on trial from when it's installed until it passes.
grep -q '^greenboot_next_deployment_id=' <<<"$vars" || exit 0
# The boot menu fell back to the previous version, which is known to work.
grep -qx 'boot_counter=-1' <<<"$vars" && exit 0
exec /usr/libexec/evenkeel-os-health compare
