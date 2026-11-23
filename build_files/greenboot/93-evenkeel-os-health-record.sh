#!/usr/bin/bash
# After a good start: save what works, once slow devices have had 4 minutes (the service waits; greenboot doesn't).
systemctl start --no-block evenkeel-os-health-record.service
