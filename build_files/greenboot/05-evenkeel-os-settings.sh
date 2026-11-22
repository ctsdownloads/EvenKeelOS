#!/usr/bin/bash
# Important system settings in /etc have to be there; a missing one fails the start, and red.d puts it back.
exec /usr/libexec/evenkeel-os-settings check
