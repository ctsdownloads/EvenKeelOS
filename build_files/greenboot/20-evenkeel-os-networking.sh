#!/usr/bin/bash
# Networking has to start within 3 minutes; being offline is fine.
for _ in $(seq 180); do
  systemctl -q is-active NetworkManager.service && exit 0
  systemctl -q is-failed NetworkManager.service && break
  sleep 1
done
echo "Networking (NetworkManager.service) did not start."
exit 1
