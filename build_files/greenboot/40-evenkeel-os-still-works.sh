#!/usr/bin/bash
# A new version on trial must keep working what worked at the last good start (runs after the login check, 30).
exec /usr/libexec/evenkeel-os-health trial
