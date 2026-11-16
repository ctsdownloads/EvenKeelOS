#!/usr/bin/bash
# While a new version is on trial, a login has to reach a working desktop. A login with no desktop after a minute,
# or two logins that end within a minute (a login loop), fail the start. No verdict within 15 minutes passes.
grub2-editenv - list 2>/dev/null | grep -q '^boot_counter=' || exit 0
declare -A first_seen judged
fails=0
end=$((SECONDS + 900))
while [ "$SECONDS" -lt "$end" ]; do
  live=" "
  while read -r id; do
    [ -n "$id" ] || continue
    [ "$(loginctl show-session "$id" -p Class --value 2>/dev/null)" = user ] || continue
    case "$(loginctl show-session "$id" -p Type --value 2>/dev/null)" in wayland|x11) ;; *) continue ;; esac
    live+="$id "
    [ -n "${judged[$id]:-}" ] && continue
    first_seen[$id]=${first_seen[$id]:-$SECONDS}
    [ $((SECONDS - first_seen[$id])) -ge 60 ] || continue
    judged[$id]=1
    user=$(loginctl show-session "$id" -p Name --value)
    if pgrep -u "$user" -x gnome-shell >/dev/null; then
      echo "A login reached the desktop."
      exit 0
    fi
    echo "Login session $id for $user has no desktop after a minute."
    exit 1
  done < <(loginctl list-sessions --no-legend | awk '{print $1}')
  for id in "${!first_seen[@]}"; do
    if [ -z "${judged[$id]:-}" ] && [[ $live != *" $id "* ]]; then
      judged[$id]=1
      echo "Login session $id ended within a minute."
      fails=$((fails + 1))
    fi
  done
  if [ "$fails" -ge 2 ]; then
    echo "Two logins didn't reach a working desktop (a login loop)."
    exit 1
  fi
  sleep 5
done
echo "No login reached the desktop or failed within 15 minutes."
