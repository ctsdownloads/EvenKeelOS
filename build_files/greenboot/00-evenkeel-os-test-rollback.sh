#!/usr/bin/bash
# The test copy made by System Tools' Test automatic rollback fails here on purpose.
if tr ' ' '\n' </proc/cmdline | grep -qx 'evenkeel_os.test_rollback=1'; then
  echo "Test of automatic rollback: this test copy fails on purpose."
  exit 1
fi
