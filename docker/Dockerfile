# syntax=docker/dockerfile:1
#
# Multi-stage build:
#
#   builder     – builds a wheel from local source and installs it into /opt/venv. No PyPI fetch; the image
#                 reflects exactly the source at build time.
#   production  – default; clean runtime image. Built by CI (docker.yaml).
#
# Drop-in replacement for the old ghcr.io/3ll3d00d/cmdserver-image: same port, same config lookup
# (CMDSERVER_CONFIG_HOME if set, else ~/.cmdserver), runs as root like before so existing volume mappings keep
# working.

# python:3.13-slim-trixie: Debian 13 (stable), native Python 3.13
FROM python:3.13-slim-trixie AS base

WORKDIR /app

VOLUME ["/config"]

# OCI image annotations. image.source lets GHCR link the package to its GitHub repo on push.
ARG REPO_URL=""
ARG REPO_DESCRIPTION="cmdserver: web based home cinema automation, including JVC projector control"
# net.unraid.docker.icon gives the container its icon in the Unraid Docker tab without a `-l` on the run command.
LABEL org.opencontainers.image.source=$REPO_URL \
      org.opencontainers.image.description=$REPO_DESCRIPTION \
      net.unraid.docker.icon="https://raw.githubusercontent.com/3ll3d00d/cmdserver/master/img/icon.png"

EXPOSE 53199

# ── Builder: build a wheel from local source + install it ────────────────────
# The package version is derived from the git tag by hatch-vcs, but .git is excluded from the build context, so CI
# passes it in via CMDSERVER_VERSION; local builds without it get a placeholder. On tag builds CI also writes
# cmdserver/VERSION before `docker build`, which is what /api/1/version reports.
FROM base AS builder

ARG CMDSERVER_VERSION=0.0.0+unknown

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY cmdserver/ ./cmdserver/

RUN --mount=type=cache,target=/root/.cache/pip \
    SETUPTOOLS_SCM_PRETEND_VERSION="${CMDSERVER_VERSION}" pip install .

# ── Production: clean runtime image ──────────────────────────────────────────
FROM base AS production

# curl is only needed for the healthcheck
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && apt-get install --no-install-recommends -y curl

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

HEALTHCHECK --interval=10s --timeout=2s --start-period=20s \
  CMD curl -f -s --show-error http://localhost:53199/api/1/version || exit 1

CMD ["cmdserver"]
