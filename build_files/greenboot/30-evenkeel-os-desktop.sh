#!/usr/bin/bash
# On trial, a login must reach the desktop within a minute and not end within a minute twice; 15 minutes passes.
vars=$(grub2-editenv /boot/grub2/grubenv list)
# greenboot names the version on trial from when it's installed until it passes.
grep -q '^greenboot_next_deployment_id=' <<<"$vars" || exit 0
# The boot menu fell back to the previous version, which is known to work.
grep -qx 'boot_counter=-1' <<<"$vars" && exit 0
# systemd-logind's "new session" and "session removed" records
started=8d45620c1a4348dbb17410da57c60c66
removed=3354939424b4456d9802ca8333ed424a
end=$((SECONDS + 900))
while [ "$SECONDS" -lt "$end" ]; do
  now=$(date +%s%6N)
  declare -A gone=()
  while read -r id t; do
    gone[$id]=$t
  done < <(journalctl -b -q -o json "MESSAGE_ID=$removed" | jq -r '"\(.SESSION_ID) \(.__REALTIME_TIMESTAMP)"')
  fails=0
  while read -r id user t; do
    if [ -n "${gone[$id]:-}" ]; then
      [ $((gone[$id] - t)) -lt 60000000 ] && fails=$((fails + 1))
    elif [ $((now - t)) -ge 60000000 ]; then
      if pgrep -u "$user" -x gnome-shell >/dev/null; then
        echo "A login reached the desktop."
        exit 0
      fi
      echo "Login session $id for $user has no desktop after a minute."
      exit 1
    fi
  done < <(journalctl -b -q -o json "MESSAGE_ID=$started" \
             | jq -r 'select(.CLASS == "user" and (.TYPE == "wayland" or .TYPE == "x11"))
                      | "\(.SESSION_ID) \(.USER_ID) \(.__REALTIME_TIMESTAMP)"')
  if [ "$fails" -ge 2 ]; then
    echo "Two logins didn't reach a working desktop (a login loop)."
    exit 1
  fi
  sleep 2
done
echo "No login reached the desktop or failed within 15 minutes."
