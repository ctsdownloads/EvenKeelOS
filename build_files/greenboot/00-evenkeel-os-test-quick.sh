#!/usr/bin/bash
# The quick test copy made by Wheelhouse's Test automatic rollback fails here on purpose.
if tr ' ' '\n' </proc/cmdline | grep -qx 'evenkeel_os.test_rollback=quick'; then
  echo "Test of automatic rollback: this test copy fails on purpose."
  exit 1
fi
