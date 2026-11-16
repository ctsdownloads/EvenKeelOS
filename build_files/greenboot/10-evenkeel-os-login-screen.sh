#!/usr/bin/bash
# The login screen has to start within 3 minutes.
for _ in $(seq 180); do
  systemctl -q is-active display-manager.service && exit 0
  systemctl -q is-failed display-manager.service && break
  sleep 1
done
echo "The login screen (display-manager.service) did not start."
exit 1
