#!/usr/bin/bash
# Splits a built image into small layers, for smaller updates and an install that fits a live USB: rechunk.sh IMAGE TAG
set -euo pipefail
image=localhost/$1:$2
graphroot=$(podman info --format '{{.Store.GraphRoot}}')
podman run --rm --pull=never --privileged \
  --mount=type=image,src="$image",target=/rpm-ostree \
  --mount=type=bind,src="$graphroot",target=/run/host-container-storage,rw \
  --mount=type=tmpfs,target=/run/rpm-ostree-storage \
  --entrypoint /usr/bin/rpm-ostree "$image" \
  compose build-chunked-oci --max-layers 127 --format-version=2 --bootc --rootfs /rpm-ostree \
  --output "containers-storage:[overlay@/run/host-container-storage+/run/rpm-ostree-storage]$image"
