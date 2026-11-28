# shellcheck shell=bash
# Shared by boot-check and boot-check-root: one PASS or FAIL line per check; failed is 1 after any FAIL.
# shellcheck disable=SC2034  # read by the scripts that source this file
failed=0
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; failed=1; }
wait_for() {      # $1: seconds; the rest: a command, tried once a second until it succeeds
  local seconds=$1
  shift
  for _ in $(seq "$seconds"); do
    "$@" && return 0
    sleep 1
  done
  return 1
}
