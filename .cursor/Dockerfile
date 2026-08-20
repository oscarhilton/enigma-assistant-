# Cursor Cloud Agent base for personal-enigma (Node + pnpm + uv + Python 3.12).
# Cursor clones the repo at job start; do not COPY the project into this image.
FROM node:22-bookworm-slim

ARG PNPM_VERSION=10.3.0
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
ENV UV_PYTHON=python3.12

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        sudo \
        curl \
        ca-certificates \
        python3.12 \
        python3.12-venv \
        jq \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.12 /usr/bin/python3

RUN corepack enable && corepack prepare "pnpm@${PNPM_VERSION}" --activate

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=ghcr.io/astral-sh/uv:latest /uvx /usr/local/bin/uvx

RUN useradd -m -s /bin/bash ubuntu \
    && echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ubuntu \
    && chmod 0440 /etc/sudoers.d/ubuntu

WORKDIR /workspace
RUN chown ubuntu:ubuntu /workspace
USER ubuntu
