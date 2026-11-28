# Allow build scripts to be referenced without being copied into the final image
FROM scratch AS ctx
COPY build_files /
COPY cosign.pub /evenkeel-os.pub
COPY system_files /system_files
COPY po /po

FROM quay.io/fedora-ostree-desktops/silverblue:45

RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache \
    --mount=type=cache,dst=/var/log \
    --mount=type=tmpfs,dst=/tmp \
    /ctx/build.sh

LABEL org.opencontainers.image.source="https://github.com/ctsdownloads/EvenKeelOS"

RUN bootc container lint
