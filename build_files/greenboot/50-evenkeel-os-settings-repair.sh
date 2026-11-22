#!/usr/bin/bash
# After a failed start: put back missing settings from the copy saved at the last good start.
exec /usr/libexec/evenkeel-os-settings repair
