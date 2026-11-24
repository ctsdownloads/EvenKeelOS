#!/usr/bin/bash
# Boot test: start the new image in a virtual machine on the build machine and check it reaches the desktop.
# Usage: boot_test/run-boot-test.sh IMAGE   (IMAGE in this user's podman storage; results in boot-test-results/)
set -euo pipefail

IMAGE=$1
# The disk tool, locked to one version; a newer one is taken by changing this line in a pull request.
BIB=quay.io/centos-bootc/bootc-image-builder@sha256:dab86ee6b46dcade411b37f4e70b07d93b6a06da0dbfec6fe89247a220e0d9f8
TEST_IMAGE=localhost/evenkeel-os-boot-test:latest
OUT=${RUNNER_TEMP:-/tmp}/boot-test-results
SSH_WAIT=600                 # seconds a start may take before it counts as failed
. "$(dirname "$0")/vm.sh"
# The disk and key are kept in $VM for the rollback tests.
sudo rm -rf "$VM"
mkdir -p "$OUT" "$VM"
: > "$OUT/report.txt"

summary() { [ -n "${GITHUB_STEP_SUMMARY:-}" ] && echo "$1" >> "$GITHUB_STEP_SUMMARY"; return 0; }

# The virtual machine runs as root, so its screenshots and logs are handed back for the upload step.
trap 'sudo chown -R "$(id -u):$(id -g)" "$OUT" || true' EXIT
# A step that stops the script still leaves a line in the report and the summary.
trap 'say "FAIL: the boot test stopped at line $LINENO, before the checks finished."; \
      summary "Boot test failed before the checks finished. The details are in the build log."' ERR

if [ ! -e /dev/kvm ]; then
  say "FAIL: this build machine can't run virtual machines (no /dev/kvm), so the boot test can't run."
  summary "Boot test: couldn't run, this build machine can't run virtual machines."
  exit 1
fi

# The test copy: the new image plus autologin, SSH and the checks. It goes to root's storage for the disk tool.
podman build --build-arg "BASE=$IMAGE" -f boot_test/Containerfile -t "$TEST_IMAGE" .
podman image prune -f
podman save --format docker-archive "$TEST_IMAGE" | sudo podman load
podman rmi "$TEST_IMAGE"
df -h / | tee -a "$OUT/disk-space.txt"

# The test user's key and password exist only for this run.
ssh-keygen -q -t ed25519 -N '' -C boot-test -f "$VM/key"
hash=$(openssl passwd -6 "$(openssl rand -hex 16)")
cat > "$VM/config.toml" <<TOML
[[customizations.user]]
name = "tester"
password = "$hash"
key = "$(cat "$VM/key.pub")"
groups = ["wheel"]

# Room for the rollback tests' second version of the image.
[[customizations.filesystem]]
mountpoint = "/"
minsize = "40 GiB"
TOML

mkdir -p "$VM/output"
sudo podman run --rm --privileged --pull=missing --security-opt label=type:unconfined_t \
  -v "$VM/config.toml:/config.toml:ro" -v "$VM/output:/output" \
  -v /var/lib/containers/storage:/var/lib/containers/storage \
  "$BIB" --type qcow2 --rootfs xfs "$TEST_IMAGE"
sudo podman rmi "$TEST_IMAGE"
df -h / | tee -a "$OUT/disk-space.txt"
if ! sudo test -s "$DISK"; then
  say "FAIL: the test disk wasn't made."
  summary "Boot test: the test disk wasn't made."
  exit 1
fi

attempt() {
  local n=$1 rc
  # -snapshot: every start begins from the freshly made disk, so a second try is a clean first start.
  vm_start "$OUT/serial-$n.log" -snapshot
  say "Start $n:"
  rc=1
  local deadline=$((SECONDS + SSH_WAIT))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if "${SSH[@]}" true 2>/dev/null; then rc=0; break; fi
    sleep 5
  done
  if [ "$rc" -ne 0 ]; then
    say "FAIL: the computer didn't start far enough to be checked within $((SSH_WAIT / 60)) minutes."
  else
    "${SSH[@]}" /usr/libexec/evenkeel-os-boot-check > "$VM/checks.txt" 2>&1 && rc=0 || rc=1
    tee -a "$OUT/report.txt" < "$VM/checks.txt"
    "${SSH[@]}" journalctl -b -p warning --no-pager > "$OUT/warnings-$n.txt" 2>&1 || true
  fi
  vm_monitor "screendump $OUT/desktop-$n.png -f png" || true
  sleep 2
  [ -s "$OUT/desktop-$n.png" ] || say "Note: the screenshot of start $n couldn't be taken."
  vm_stop || true
  return "$rc"
}

if attempt 1 || { say "Trying once more from a clean start."; attempt 2; }; then
  say "Boot test passed."
  summary "Boot test passed: the new version started and reached the desktop, and Logo Menu, ArcMenu, Dash to \
Panel and System Tools work. The screenshot is in the boot-test download."
  exit 0
fi
say "Boot test failed. Nothing is published."
summary "Boot test failed, so nothing is published. The report and screenshot are in the boot-test download."
exit 1
