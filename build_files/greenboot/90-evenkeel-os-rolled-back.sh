#!/usr/bin/bash
# After greenboot goes back to the previous version: a note for the next login, and a 3-day pause on automatic updates.
# After System Tools' test, the test copy is removed instead of pausing.
note=/var/lib/evenkeel-os/rolled-back
pause=/var/lib/evenkeel-os/updates-paused-until
journalctl -b -u greenboot-healthcheck.service -o cat --no-pager \
  | grep -qE 'deployment has been rolled back|Rollback successful|Rollback to previous deployment completed' || exit 0
mkdir -p "${note%/*}"
if grep -qs 'evenkeel_os.test_rollback=1' /boot/loader/entries/*.conf; then
  rpm-ostree cleanup -r || echo "The test copy could not be removed."
  echo "test $(date +%s)" >"$note"
else
  systemctl -q is-enabled uupd.timer && echo $(( $(date +%s) + 3 * 86400 )) >"$pause"
  echo "update $(date +%s)" >"$note"
fi
chmod 644 "$note"
