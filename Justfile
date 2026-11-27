set dotenv-filename := "image-template.env"
set dotenv-load

export image_name := env_var("IMAGE_NAME")
export repo_organization := env_var("REPO_ORGANIZATION")
export image_desc := env_var("IMAGE_DESC")
export default_tag := env_var("DEFAULT_TAG")

# The commit, when the working tree has no changes: it names the image's labels and tags.
git_sha := `[ -z "$(git status -s)" ] && git rev-parse --short HEAD || true`

[private]
default:
    @just --list

# Check the Justfile's syntax
check:
    just --unstable --fmt --check -f Justfile

# Build the image
build $target_image=image_name $tag=default_tag:
    #!/usr/bin/env bash

    set -euox pipefail

    LABELS=()
    GIT_SHA="{{ git_sha }}"
    if [[ -n "${GIT_SHA}" ]]; then
        LABELS+=("--label" "org.opencontainers.image.documentation=https://raw.githubusercontent.com/{{ repo_organization }}/{{ image_name }}/${GIT_SHA}/README.md")
        LABELS+=("--label" "org.opencontainers.image.source=https://github.com/{{ repo_organization }}/{{ image_name }}/blob/${GIT_SHA}/Containerfile")
        LABELS+=("--label" "org.opencontainers.image.url=https://github.com/{{ repo_organization }}/{{ image_name }}/tree/${GIT_SHA}")
        LABELS+=("--label" "org.opencontainers.image.version={{ default_tag }}.$(date +%Y%m%d)-${GIT_SHA}")
    fi

    LABELS+=("--label" "org.opencontainers.image.created=$(date -u +%Y\-%m\-%d\T%H\:%M\:%S\Z)")
    LABELS+=("--label" "org.opencontainers.image.description={{ image_desc }}")
    LABELS+=("--label" "org.opencontainers.image.licenses=GPL-3.0-or-later")
    LABELS+=("--label" "org.opencontainers.image.title={{ image_name }}")
    LABELS+=("--label" "org.opencontainers.image.vendor={{ repo_organization }}")

    podman build "${LABELS[@]}" --pull=newer --tag "${target_image}:${tag}" --file Containerfile .

# Split the image into layers for smaller updates
ostree-rechunk $target_image=image_name $tag=default_tag:
    build_files/rechunk.sh "${target_image}" "${tag}"

generate-default-tag $tag=default_tag:
    @echo "${tag}"

generate-build-tags $target_image=image_name $tag=default_tag:
    #!/usr/bin/env bash
    set -eoux pipefail

    DATE=$(date +%Y%m%d)
    BUILD_TAGS=()
    GIT_SHA="{{ git_sha }}"
    if [[ -n "${GIT_SHA}" ]]; then
        BUILD_TAGS+=("${tag}-${GIT_SHA}")
        BUILD_TAGS+=("${tag}-${DATE}-${GIT_SHA}")
        BUILD_TAGS+=("${DATE}-${GIT_SHA}")
    fi

    BUILD_TAGS+=("${DATE}")
    BUILD_TAGS+=("${tag}")
    BUILD_TAGS+=("${tag}-${DATE}")

    echo "${BUILD_TAGS[@]}"

tag-images $target_image=image_name $tag=default_tag tags="":
    #!/usr/bin/env bash
    set -eoux pipefail

    IMAGE=$(podman inspect ${target_image}:${tag} | jq -r .[].Id)
    podman untag ${IMAGE}

    for tag in {{ tags }}; do
        podman tag $IMAGE "${target_image}:${tag}"
    done

    podman images

[private]
image_name:
    @echo "${image_name}"
