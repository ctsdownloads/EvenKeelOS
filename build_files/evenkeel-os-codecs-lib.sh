# Shared by the codecs tool and its root helpers; sourced only. Nothing here comes from the caller.
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
umask 022

STATE=/var/lib/evenkeel-os
OPEN=$STATE/codecs-setup-open        # exists during the one-time setup window
DONE=$STATE/codecs-setup-done        # exists once the setup question has been answered
WINDOW_MINUTES=1440                  # the setup window lasts 24 hours at most

window_open() { [ ! -e "$DONE" ] && [ -n "$(find "$OPEN" -maxdepth 0 -mmin -"$WINDOW_MINUTES" 2>/dev/null)" ]; }

# Everything: RPM Fusion free, copied into /etc only when chosen; key from distribution-gpg-keys.
REPO_DIR=/usr/share/evenkeel-os
REPOS="rpmfusion-free.repo rpmfusion-free-updates.repo"
FREE="ffmpeg-free libavcodec-free libavdevice-free libavfilter-free libavformat-free libavutil-free libswresample-free libswscale-free"
FULL="ffmpeg ffmpeg-libs libavdevice x264-libs x265-libs"
WEB="openh264 mozilla-openh264 gstreamer1-plugin-openh264"
# Fedora's OpenH264 stand-in: web removes it in the same step, remove puts it back.
STAND_IN="noopenh264"

# Earlier EvenKeelOS builds used negativo17. These are only used to remove that setup cleanly.
OLD_REPO=/etc/yum.repos.d/negativo17-multimedia.repo
OLD_FULL="ffmpeg ffmpeg-libs libavcodec libavdevice libavfilter libavformat libavutil libswresample libswscale x264-libs x265-libs"
OLD_REPLACE="xevd-libs xeve-libs"

log()    { logger -t evenkeel-os-codecs -- "$*"; }
caller() { printf '%s' "${PKEXEC_UID:-unknown}"; }
present() { local p; for p in "$@"; do rpm -q "$p" >/dev/null 2>&1 && printf '%s ' "$p"; done; }
need_root() { [ "$(id -u)" -eq 0 ] || { echo "This helper must run as root, through polkit."; exit 1; }; }

# Names in rpm-ostree's request ($1) that are also in the list given.
requested() {
  local field=$1; shift
  rpm-ostree status --json | python3 -I -c '
import json, sys
d = json.load(sys.stdin)["deployments"][0]
want = set(sys.argv[2:])
print(" ".join(sorted(set(d.get(sys.argv[1], [])) & want)))' "$field" "$@"
}

old_setup_present() {   # anything left from the negativo17 version
  [ -e "$OLD_REPO" ] && return 0
  [ "$(rpm -q --qf '%{EPOCH}' xevd-libs 2>/dev/null)" = 1 ] && return 0
  [ -n "$(requested requested-packages libavcodec libavfilter libavformat libavutil libswresample libswscale)" ]
}

repos_on()  { local r; for r in $REPOS; do install -m 0644 "$REPO_DIR/$r" "/etc/yum.repos.d/$r" || return 1; done; }
repos_off() { local r; for r in $REPOS; do grep -qs 'EvenKeelOS' "/etc/yum.repos.d/$r" && rm -f "/etc/yum.repos.d/$r"; done; return 0; }

# Run and show output; on failure keep a full copy in the journal (-t evenkeel-os-codecs).
run_logged() {
  local out rc
  out=$("$@" 2>&1); rc=$?
  printf '%s\n' "$out"
  [ "$rc" -eq 0 ] || printf '%s\n' "$out" | logger -t evenkeel-os-codecs
  return "$rc"
}

do_web() {
  if [ -n "$(requested requested-base-removals $STAND_IN)" ]; then   # already chosen, booted or pending
    echo "Web video is already installed. Restart if you have not yet."; return 0
  fi
  local cmd=(override remove "$STAND_IN") p
  for p in $WEB; do cmd+=(--install "$p"); done
  run_logged rpm-ostree "${cmd[@]}"
}

do_full() {
  if old_setup_present; then
    echo "error: codecs from an earlier version of this system (negativo17) are still installed."
    echo "Remove them first: run  codecs remove , restart, then choose Everything again."
    return 1
  fi
  if [ -n "$(requested requested-base-removals ffmpeg-free)" ]; then   # already chosen, booted or pending
    echo "The full codecs are already installed. Restart if you have not yet."; return 0
  fi
  repos_on || return 1
  local cmd=(override remove) p
  for p in $(present $FREE); do cmd+=("$p"); done
  for p in $FULL; do cmd+=(--install "$p"); done
  if ! run_logged rpm-ostree "${cmd[@]}"; then
    repos_off
    echo "The change was not made, and nothing was left behind."
    return 1
  fi
}

do_remove() {
  local uninstall resets old_replaced="" p cmd
  uninstall=$(requested requested-packages $FULL $OLD_FULL $WEB)
  resets=$(requested requested-base-removals $FREE $STAND_IN)
  [ "$(rpm -q --qf '%{EPOCH}' xevd-libs 2>/dev/null)" = 1 ] && old_replaced="$OLD_REPLACE"
  if [ -n "$resets$old_replaced" ]; then
    local -a reset_list
    read -ra reset_list <<<"$resets $old_replaced"
    cmd=(override reset "${reset_list[@]}")
    for p in $uninstall; do cmd+=(--uninstall "$p"); done
    run_logged rpm-ostree "${cmd[@]}" || return 1
  elif [ -n "$uninstall" ]; then
    run_logged rpm-ostree uninstall $uninstall || return 1
  fi
  repos_off
  rm -f "$OLD_REPO"
  echo "Removed. Restart to finish."
}
