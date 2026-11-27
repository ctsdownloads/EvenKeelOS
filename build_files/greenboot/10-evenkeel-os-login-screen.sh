#!/usr/bin/bash
# The login screen has to start within 3 minutes.
exec /usr/libexec/evenkeel-os-wait-started display-manager.service "The login screen"
