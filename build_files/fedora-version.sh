#!/bin/bash
# The Fedora version the image is built on, read from the Containerfile; run from the repo root.
set -euo pipefail
v=$(sed -n 's|^FROM quay.io/fedora-ostree-desktops/silverblue:\([0-9][0-9]*\)$|\1|p' Containerfile)
[ -n "$v" ] || { echo "ERROR: no Fedora version found in the Containerfile" >&2; exit 1; }
echo "$v"
