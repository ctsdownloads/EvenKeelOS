#!/usr/bin/bash
# Rollback tests: each Test automatic rollback test run for real on the boot test's disk, as a person would.
# Usage: boot_test/run-rollback-tests.sh   (after run-boot-test.sh; results in rollback-test-results/)
set -uo pipefail

OUT=${RUNNER_TEMP:-/tmp}/rollback-test-results
HERE=$(dirname "$0")
. "$HERE/vm.sh"
# System Tools' tests, less the two a virtual machine has no chip for: Wi-Fi and Bluetooth.
mapfile -t TESTS < <(python3 -I - "$HERE/../build_files/evenkeel-os-tools-admin" <<'PY'
import ast, sys
for n in ast.parse(open(sys.argv[1]).read()).body:
    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "TEST_KINDS":
        print("\n".join(k for k in ast.literal_eval(n.value) if k not in ("wifi", "bluetooth")))
PY
)
# The tests that ask first before each restart: those checked after login (evenkeel-os-tools).
mapfile -t ASKS < <(python3 -I - "$HERE/../build_files/evenkeel-os-tools" <<'PY'
import ast, sys
for n in ast.parse(open(sys.argv[1]).read()).body:
    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "AFTER_LOGIN_TESTS":
        print("\n".join(ast.literal_eval(n.value)))
PY
)
WAIT=90             # seconds from staging to the restart: longer than rpm-ostreed's old 60-second idle exit
TEST_TIME=1800      # seconds one test may take, all 3 starts
STEP=/usr/libexec/evenkeel-os-rollback-step
# A sound card, and a crash stops the virtual machine so it can be started again like the power button.
DEVICES=(-device intel-hda -audiodev "none,id=snd" -device "hda-duplex,audiodev=snd"
         -device pvpanic -action "panic=shutdown")
mkdir -p "$OUT"
: > "$OUT/report.txt"
trap 'sudo chown -R "$(id -u):$(id -g)" "$OUT" || true' EXIT

failed=0
why=""
fail() { say "FAIL: $1"; failed=1; }
step() { on sudo -n "$STEP" "$@"; }
boot_id() { on cat /proc/sys/kernel/random/boot_id; }
# Runs a step that restarts the computer, then waits for the new start (a different boot ID) to answer.
# On failure $why says what went wrong (exit 255 is SSH cut off by the restart itself).
restart_by() {
  local before end out rc now
  before=$(boot_id) || { why="the computer didn't answer"; return 1; }
  out=$(step "$@" 2>&1)
  rc=$?
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 255 ]; then why="$1 was refused (exit $rc): $out"; return 1; fi
  end=$((SECONDS + 900))
  while [ "$SECONDS" -lt "$end" ]; do
    sleep 15
    keep_on
    now=$(boot_id) && [ -n "$now" ] && [ "$now" != "$before" ] && return 0
  done
  why="the computer didn't restart within 15 minutes"
  return 1
}
restart_after_wait() { sleep "$WAIT"; restart_by restart; }
# The next start, after the wait (none for "now"): stops the run when it doesn't come up ready. $1: ready's "settled".
next_start() {
  if [ "${1:-}" = now ]; then shift; restart_by restart; else restart_after_wait; fi || { fail "$why"; exit 1; }
  ready "$@" || { fail "the computer wasn't ready within 15 minutes of starting."; exit 1; }
}
# A person's part: turn it on after a crash, and reset it when it stops answering for 20 minutes.
keep_on() {
  if ! vm_running; then
    say "  It was off after a crash; turning it on."
    vm_start "$OUT/serial-$(date +%s).log" "${DEVICES[@]}"
    seen=$SECONDS
  elif on true; then
    seen=$SECONDS
  elif [ $((SECONDS - seen)) -gt 1200 ]; then
    say "  No answer for 20 minutes; pressing reset."
    vm_monitor system_reset
    seen=$SECONDS
  fi
}
# Up, on no test copy, with greenboot done and a list of what works saved; "settled": saved by this start, so
# nothing else asks rpm-ostreed anything afterwards (the control watches its idle exit).
ready() {
  local end=$((SECONDS + 900)) rec=/var/lib/evenkeel-os/health-record.json saved
  saved="test -s $rec"
  [ "${1:-}" = settled ] && saved="[ \"\$(stat -c %Y $rec)\" -gt \"\$(date -d \"\$(uptime -s)\" +%s)\" ]"
  while [ "$SECONDS" -lt "$end" ]; do
    keep_on
    on "! grep -q evenkeel_os.test_rollback= /proc/cmdline && systemctl -q is-active greenboot-healthcheck && $saved" &&
      return 0
    sleep 10
  done
  return 1
}
# The window before an automatic restart (evenkeel-os-tools restart-question): its zenity's process ID, if open.
# [z] and [p]: the pattern doesn't match the shell running pgrep.
WINDOW='[z]enity --title=Automatic rollback --width=520 --question'
window_pid() { on "pgrep -u tester -f -- '$WINDOW' | head -1"; }
# Saves the open window's words to $1 and presses keys on it, as a person would (QEMU's keyboard).
answer() {
  local file=$1 pid=$2
  shift 2
  on "tr '\\0' '\\n' < /proc/$pid/cmdline" > "$file"
  sleep 3
  for k in "$@"; do vm_monitor "sendkey $k"; sleep 1; done
}
# $1: how greenboot must have found the versions (bootc or rpm-ostree) when marking the new one at the shutdown.
marked() {
  on journalctl -b -1 -u greenboot-set-rollback-trigger -o cat > "$OUT/marking.txt"
  grep -q "System detected as ${1:-rpm-ostree}" "$OUT/marking.txt" &&
    grep -q "Setting rollback trigger" "$OUT/marking.txt"
}

# Empty when a test asked first on both bad starts as it should (or isn't one that asks); else what went wrong.
asked_twice() {
  local kind=$1 f1="$OUT/window-$1-1.txt" f2="$OUT/window-$1-2.txt" last="and the test copy is removed. At login"
  [[ " ${ASKS[*]} " == *" $kind "* ]] || return 0
  if [ "$windows" != 2 ]; then
    echo "it asked $windows times, not on both bad starts."
  elif ! grep -q "the test is working" "$f1" || grep -q "$last" "$f1"; then
    echo "the first window's words are wrong (window-$kind-1.txt)."
  elif ! grep -q "$last" "$f2"; then
    echo "the second window's words are wrong (window-$kind-2.txt)."
  fi
}

[ "${#ASKS[@]}" -gt 5 ] || { fail "the tests that ask first couldn't be read from evenkeel-os-tools."; exit 1; }
[ "${#TESTS[@]}" -gt 5 ] || { fail "the list of tests couldn't be read from evenkeel-os-tools-admin."; exit 1; }
vm_start "$OUT/serial-first.log" "${DEVICES[@]}"
seen=$SECONDS
ready || { fail "the computer didn't start."; exit 1; }
say "A real update staged by bootc, as automatic updates do on an install with no added packages:"
step bootc-update > "$OUT/bootc-update.txt" 2>&1 || { fail "the update wasn't staged (see bootc-update.txt)."; exit 1; }
next_start
free_vm=$(on df -h --output=avail /var | tail -1)
say "  Free space: here $(df -h --output=avail / | tail -1), in the virtual machine $free_vm"
if ! on 'test -e /usr/share/evenkeel-os-boot-test/next'; then fail "the update didn't start."
elif marked bootc; then say "PASS: the update was marked for trial and passed its checks."
else fail "the update wasn't marked for trial (marking.txt)."; fi

# greenboot asks rpm-ostreed (not bootc) only once packages are added, as on most computers in use.
say "Adding a package the way Install Package File does."
step add-package > "$OUT/add-package.txt" 2>&1 || { fail "the package wasn't added (add-package.txt)."; exit 1; }
next_start now settled

say "The failure this image fixes, with rpm-ostreed's old 60-second idle exit:"
step idle-exit 60 && step mark-test append || { fail "the old setting or the new version couldn't be made."; exit 1; }
next_start settled
if ! on 'grep -q evenkeel_os.boot_test=1 /proc/cmdline'; then
  fail "the new version didn't start, so the old setting wasn't shown."
elif marked; then
  fail "the new version was marked for trial even with the old setting, so this test can't show the fix."
else
  say "PASS: as on the laptop, the new version wasn't marked for trial."
fi
step idle-exit 0 && step mark-test delete || { fail "the fix or the next version couldn't be made."; exit 1; }
next_start
if on 'grep -q evenkeel_os.boot_test=1 /proc/cmdline'; then fail "the next version didn't start."
elif marked; then say "PASS: with the fix, the new version was marked for trial."
else fail "the fix didn't mark the new version for trial."; fi

# Important settings deleted needs an earlier version to fall back to; there is one now.
say "Test: settings"
since=$(on date +%s) || since=0
if ! restart_by settings-test; then
  fail "settings: $why"
else
  end=$((SECONDS + TEST_TIME))
  result=timeout
  while [ "$SECONDS" -lt "$end" ]; do
    keep_on
    read -r kind at _ < <(on 'systemctl -q is-active greenboot-healthcheck &&
                                head -1 /var/lib/evenkeel-os/settings-repaired') || kind=""
    if [ "${kind:-}" = test ] && [ "${at:-0}" -gt "$since" ]; then result=pass; break; fi
    back=$(on cat /var/lib/evenkeel-os/rolled-back) || back=""
    if [ "${back%% *}" = settings-test ] && [ "${back##* }" -gt "$since" ]; then result=back; break; fi
    sleep 20
  done
  on "journalctl --since=@$since -u greenboot-healthcheck -o short --no-pager" > "$OUT/greenboot-settings.txt"
  case $result in
    pass) say "PASS: settings were deleted for real and put back by themselves." ;;
    back) fail "settings weren't put back; the computer went back to the earlier version instead." ;;
    *) fail "settings weren't put back within $((TEST_TIME / 60)) minutes." ;;
  esac
fi

for kind in "${TESTS[@]}"; do
  say "Test: $kind"
  ready || { fail "$kind: the computer wasn't ready within 15 minutes."; break; }
  since=$(on date +%s) || since=""
  [ -n "$since" ] || { fail "$kind: the computer didn't answer."; continue; }
  out=$(step start "$kind" 2>&1)
  rc=$?
  if [ "$rc" -eq 9 ]; then
    say "SKIP: $kind: this virtual machine's driver is built in, so it can't be blocked (a laptop's can)."
    continue
  fi
  if [ "$rc" -ne 0 ]; then
    fail "$kind: the test copy wasn't made: $out"
    on 'for d in /sys/class/drm/card[0-9]* /sys/class/sound/card[0-9]*; do
          echo "$d: $(readlink -f "$d/device/driver") module $(readlink "$d/device/driver/module")"; done' \
      | sed 's/^/  driver: /' | tee -a "$OUT/report.txt"
    continue
  fi
  restart_after_wait || { fail "$kind: $why"; continue; }
  end=$((SECONDS + TEST_TIME))
  result=timeout
  login=$SECONDS
  windows=0
  last_pid=""
  while [ "$SECONDS" -lt "$end" ]; do
    keep_on
    # Each bad start of a test checked after login asks first: Enter presses Restart now, its default button.
    pid=$(window_pid) || pid=""
    # A window of a later start can have the same process ID: the start's boot ID tells them apart.
    [ -n "$pid" ] && { now=$(boot_id) && [ -n "$now" ] && pid="$now $pid" || pid=""; }
    if [ -n "$pid" ] && [ "$pid" != "$last_pid" ]; then
      windows=$((windows + 1))
      answer "$OUT/window-$kind-$windows.txt" "${pid##* }" ret
      last_pid=$pid
    fi
    # A login loop needs a second login in the same start: log in again every 2 minutes.
    if [ "$kind" = login-loop ] && [ $((SECONDS - login)) -gt 120 ] &&
       on 'grep -q test_rollback=login-loop /proc/cmdline'; then
      step log-in-again
      login=$SECONDS
    fi
    note=$(on 'grep -q evenkeel_os.test_rollback= /proc/cmdline || cat /var/lib/evenkeel-os/rolled-back') || note=""
    if [ "${note%% *}" = test ] && [ "${note##* }" -gt "$since" ] 2>/dev/null; then result=pass; break; fi
    if on 'grep -q evenkeel_os.test_rollback= /proc/cmdline &&
           journalctl -b -u greenboot-healthcheck -o cat | grep -q "health-check passed"'; then result=kept; break; fi
    sleep 20
  done
  on "journalctl --since=@$since -u greenboot-healthcheck -u greenboot-set-rollback-trigger -o short --no-pager" \
    > "$OUT/greenboot-$kind.txt"
  asked=$(asked_twice "$kind")
  if [ "$result" = pass ] && grep -q "Setting rollback trigger" "$OUT/greenboot-$kind.txt" && [ -z "$asked" ]; then
    say "PASS: $kind was marked for trial after a $WAIT-second wait and rolled back by itself."
    [ "$windows" = 0 ] || say "  It asked first on both bad starts, and Restart now restarted it."
    on 'tail -n +2 /var/lib/evenkeel-os/rolled-back-why' | sed 's/^/  found broken: /' | tee -a "$OUT/report.txt"
    continue
  fi
  case $result in
    pass) if [ -n "$asked" ]; then fail "$kind rolled back, but $asked"
          else fail "$kind rolled back, but greenboot's marking isn't in its messages."; fi ;;
    kept) fail "$kind's test copy passed its checks and stayed as the normal version." ;;
    *) fail "$kind didn't roll back within $((TEST_TIME / 60)) minutes." ;;
  esac
  step start clear && step restart && sleep 30
done
# Keep: a Boot options change that breaks printing; Esc opens the window again, then Keep with the password.
keep_test() {
  local pid again end key
  ready || { why="the computer wasn't ready within 15 minutes."; return 1; }
  step break-printing append || { why="the Boot options change wasn't made."; return 1; }
  restart_after_wait || return 1
  end=$((SECONDS + 900))
  pid=""
  while [ -z "$pid" ] && [ "$SECONDS" -lt "$end" ]; do keep_on; sleep 10; pid=$(window_pid) || pid=""; done
  [ -n "$pid" ] || { why="no window asked within 15 minutes of the start."; return 1; }
  answer "$OUT/window-keep-1.txt" "$pid" esc
  sleep 5
  again=$(window_pid) || again=""
  if [ -z "$again" ] || [ "$again" = "$pid" ]; then
    why="Esc closed the window instead of opening it again."
    return 1
  fi
  if ! grep -q "Something stopped working after the Boot options change" "$OUT/window-keep-1.txt" ||
     ! grep -q "Printing" "$OUT/window-keep-1.txt"; then
    why="the window's words are wrong (window-keep-1.txt)."
    return 1
  fi
  # Shift+Tab moves from the default button (Restart now) to Keep these options.
  answer "$OUT/window-keep-2.txt" "$again" shift-tab ret
  sleep 5
  on "pgrep -f '[p]kexec /usr/libexec/evenkeel-os-tools-admin keep-update'" >/dev/null ||
    { why="Keep these options didn't ask for the password."; return 1; }
  sleep 3
  for key in $(fold -w1 "$VM/password"); do vm_monitor "sendkey $key"; done
  vm_monitor "sendkey ret"
  end=$((SECONDS + 300))
  while [ "$SECONDS" -lt "$end" ]; do
    if on 'grep -q systemd.mask=cups.service /proc/cmdline &&
           journalctl -b -u greenboot-healthcheck -o cat | grep -q "health-check passed"'; then return 0; fi
    sleep 10
  done
  why="after the password, this start didn't pass with the change kept."
  return 1
}
say "Test: Keep, on a Boot options change that breaks printing"
if keep_test; then say "PASS: Esc opened the window again, and Keep with the password kept the change."
else fail "Keep: $why"; fi
on "journalctl -b -u greenboot-healthcheck -o short --no-pager" > "$OUT/greenboot-keep.txt"
vm_stop || true
if [ "$failed" = 0 ]; then say "Rollback tests passed: the 3 update checks, all $((${#TESTS[@]} + 1)) tests and Keep."
else say "Rollback tests failed."; fi
[ -n "${GITHUB_STEP_SUMMARY:-}" ] && tail -n 1 "$OUT/report.txt" >> "$GITHUB_STEP_SUMMARY"
exit "$failed"
