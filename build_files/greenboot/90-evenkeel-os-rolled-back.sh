#!/usr/bin/bash
# After a rollback: keep it, leave a login note, pause updates 3 days. Same saved copy as last repair: no good start.
repaired=/var/lib/evenkeel-os/settings-repaired
used=""; [ -f "$repaired" ] && used=$(awk 'NR == 1 {print $3}' "$repaired")
latest=""; [ -f /sysroot/evenkeel-os/settings/saved ] && latest=$(awk '{print $2}' /sysroot/evenkeel-os/settings/saved)
note=/var/lib/evenkeel-os/rolled-back
rolled=0
fellback=0    # the boot menu fell back by itself, not greenboot's rollback of a new version on trial
journalctl -b -u greenboot-healthcheck.service -o cat --no-pager \
  | grep -qE 'deployment has been rolled back|Rollback successful|Rollback to previous deployment completed' && rolled=1
# Greenboot can't tell a test copy from its image, so after a boot menu fallback the broken one is still the default.
if grub2-editenv /boot/grub2/grubenv list | grep -qx 'boot_counter=-1' \
   && [ "$(rpm-ostree status --json | jq -r '.deployments[0].booted')" != true ]; then
  rpm-ostree rollback || { echo "The running version couldn't be made the default."; exit 1; }
  rolled=1
  fellback=1
fi
[ "$rolled" = 1 ] || exit 0
# What the trial check found broken goes with this rollback's note only (an older list is dropped).
why=/var/lib/evenkeel-os/rolled-back-why
rm -f "$why"
[ -e /var/lib/evenkeel-os/health-lost ] && mv -f /var/lib/evenkeel-os/health-lost "$why" && chmod 644 "$why"
status=$(rpm-ostree status --json)
booted_sum=$(jq -r '.deployments[] | select(.booted) | .checksum' <<<"$status")
other_sum=$(jq -r '[.deployments[] | select(.booted | not)][0].checksum // empty' <<<"$status")
mkdir -p "${note%/*}"
# >| because greenboot runs this with noclobber.
if [ -e /var/lib/evenkeel-os/settings-test ]; then
  rm -f "$repaired"
  echo "settings-test $(date +%s)" >|"$note"
elif [ "$fellback" = 1 ] && [ -n "$used" ] && [ "$used" = "$latest" ]; then
  rm -f "$repaired"
  echo "settings-failed $(date +%s)" >|"$note"
elif grep -qs 'evenkeel_os.test_rollback=' /boot/loader/entries/*.conf; then
  rpm-ostree cleanup -r || echo "The test copy could not be removed."
  rm -f /var/lib/evenkeel-os/test-rollback-args
  echo "test $(date +%s)" >|"$note"
elif [ -n "$booted_sum" ] && [ "$booted_sum" = "$other_sum" ]; then
  # The same system with other boot options (Wheelhouse, Boot options): the update wasn't the cause, no pause.
  echo "boot-options $(date +%s)" >|"$note"
else
  if systemctl -q is-enabled uupd.timer; then /usr/libexec/evenkeel-os-tools-safe updates pause; fi
  echo "update $(date +%s)" >|"$note"
fi
chmod 644 "$note"
