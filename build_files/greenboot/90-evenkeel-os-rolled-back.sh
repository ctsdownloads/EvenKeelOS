#!/usr/bin/bash
# After going back to the previous version: keep it, a note for the next login, and a 3-day pause on automatic updates.
# After System Tools' test, the test copy is removed instead of pausing.
note=/var/lib/evenkeel-os/rolled-back
pause=/var/lib/evenkeel-os/updates-paused-until
rolled=0
journalctl -b -u greenboot-healthcheck.service -o cat --no-pager \
  | grep -qE 'deployment has been rolled back|Rollback successful|Rollback to previous deployment completed' && rolled=1
# The boot menu fell back by itself (boot_counter=-1), but greenboot can't tell two versions of the same image apart
# (a test copy differs only in its kernel arguments), so the broken one is still the default: make this one the default.
if grub2-editenv /boot/grub2/grubenv list | grep -qx 'boot_counter=-1' \
   && [ "$(rpm-ostree status --json | jq -r '.deployments[0].booted')" != true ]; then
  rpm-ostree rollback || { echo "The running version couldn't be made the default."; exit 1; }
  rolled=1
fi
[ "$rolled" = 1 ] || exit 0
mkdir -p "${note%/*}"
if grep -qs 'evenkeel_os.test_rollback=' /boot/loader/entries/*.conf; then
  rpm-ostree cleanup -r || echo "The test copy could not be removed."
  echo "test $(date +%s)" >"$note"
else
  systemctl -q is-enabled uupd.timer && echo $(( $(date +%s) + 3 * 86400 )) >"$pause"
  echo "update $(date +%s)" >"$note"
fi
chmod 644 "$note"
