# shellcheck shell=bash
# The test virtual machine, shared by the boot test and the rollback tests (sourced; needs OUT set).
VM=${RUNNER_TEMP:-/tmp}/boot-test-vm
DISK=$VM/output/qcow2/disk.qcow2
SSH=(ssh -i "$VM/key" -p 2222 -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
     -o ConnectTimeout=5 -o LogLevel=ERROR tester@127.0.0.1)

say() { echo "$1" | tee -a "$OUT/report.txt"; }
on() { "${SSH[@]}" "$@" 2>/dev/null; }
# $1: the start's message log; more QEMU options may follow.
vm_start() {
  local log=$1
  shift
  cp /usr/share/OVMF/OVMF_VARS_4M.fd "$VM/vars.fd"
  sudo rm -f "$VM/monitor.sock"
  sudo qemu-system-x86_64 -machine q35,accel=kvm -cpu host -smp 4 -m 6144 \
    -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
    -drive if=pflash,format=raw,file="$VM/vars.fd" -drive file="$DISK",if=virtio,format=qcow2 \
    -netdev user,id=net0,hostfwd=tcp:127.0.0.1:2222-:22 -device virtio-net-pci,netdev=net0 \
    -device virtio-vga -display none -monitor "unix:$VM/monitor.sock,server,nowait" \
    -serial "file:$log" -pidfile "$VM/qemu.pid" -daemonize "$@"
}
vm_monitor() { echo "$1" | sudo socat -t 5 - "UNIX-CONNECT:$VM/monitor.sock" >/dev/null; }
vm_running() { sudo test -s "$VM/qemu.pid" && sudo kill -0 "$(sudo cat "$VM/qemu.pid")" 2>/dev/null; }
vm_stop() { vm_running && sudo kill "$(sudo cat "$VM/qemu.pid")"; sleep 5; }
