#!/usr/bin/bash
# Networking has to start within 3 minutes; being offline is fine.
exec /usr/libexec/evenkeel-os-wait-started NetworkManager.service "Networking"
