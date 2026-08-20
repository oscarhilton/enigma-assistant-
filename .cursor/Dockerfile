# Cursor Cloud Agent base for personal-enigma (Node + pnpm + uv + Python 3.12).
# Cursor clones the repo at job start; do not COPY the project into this image.
#
# Debian bookworm apt ships Python 3.11 only — do NOT apt-install python3.12.
# Python 3.12 comes from `uv python install` (requires-python >=3.12,<3.15).
#
# Pin uv via multi-stage FROM (ARG expansion does not work in COPY --from=image:tag).
# Bump UV_VERSION here and in docs/cloud-agents.md together.
ARG UV_VERSION=0.12.5
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv-bin

FROM node:22-bookworm-slim

ARG PNPM_VERSION=10.3.0

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
ENV COREPACK_DEFAULT_TO_LATEST=0
ENV COREPACK_HOME=/opt/corepack
ENV UV_PYTHON=3.12
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        sudo \
        curl \
        ca-certificates \
        jq \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv-bin /uv /usr/local/bin/uv
COPY --from=uv-bin /uvx /usr/local/bin/uvx

# Shared install dir so the non-root `ubuntu` user can use the toolchain.
RUN mkdir -p /opt/uv-python \
    && uv python install 3.12 \
    && ln -sf "$(uv python find 3.12)" /usr/local/bin/python \
    && ln -sf "$(uv python find 3.12)" /usr/local/bin/python3 \
    && chmod -R a+rX /opt/uv-python

# Shared COREPACK_HOME so pnpm pin survives USER ubuntu (not only root cache).
RUN mkdir -p /opt/corepack \
    && corepack enable \
    && corepack prepare "pnpm@${PNPM_VERSION}" --activate \
    && chmod -R a+rX /opt/corepack \
    && pnpm --version

RUN useradd -m -s /bin/bash ubuntu \
    && echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ubuntu \
    && chmod 0440 /etc/sudoers.d/ubuntu

WORKDIR /workspace
RUN chown ubuntu:ubuntu /workspace
USER ubuntu
