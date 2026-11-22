# cmdserver — Agent Guide

## Project Overview

A small Flask/Twisted web app for home cinema automation: runs configured commands (e.g. JRiver zones, apps) and
controls a JVC projector over its TCP protocol, optionally publishing projector state to MQTT (used by Home
Assistant).

## Key Modules

- `cmdserver/main.py` — app setup, Twisted server
- `cmdserver/pjcontroller.py` — projector access: serialises every command behind one lock, retries refused
  commands, closes the connection after `IDLE_DISCONNECT_SECS` idle (the idle close also takes the lock, so it can
  never cut off a command in flight), refreshes state to MQTT
- `cmdserver/jvc.py` — JVC protocol / connection
- `cmdserver/jvccommands.py` — JVC command and value tables
- `cmdserver/apis/` — REST endpoints (`/api/1/...`)

## Build and test

- `uv sync`, `uv run pytest` (tests in `tests/`, no real projector needed)
- Python 3.13 is the release/CI interpreter (`.python-version`); the test matrix also covers 3.14

## Release Management

- The package version is derived from the git tag by `hatch-vcs` (`dynamic = ["version"]`); there is no version
  field to bump. A release is cut by pushing a tag (e.g. `2.1.0`). Builds without `.git` (the Docker build context)
  must set `SETUPTOOLS_SCM_PRETEND_VERSION` — `docker.yaml` passes it as the `CMDSERVER_VERSION` build arg.
  Agents must never create or push release tags.

## CI/CD

- `test.yaml` — pytest across the Python matrix; `Required checks` collapses it into one status
- `create-app.yaml` — on tags: tests, GitHub release, PyPI (trusted publishing, `release` environment), Windows exe
- `docker.yaml` — builds `docker/Dockerfile` from local source and publishes `ghcr.io/3ll3d00d/cmdserver`
  (`edge` on master, versioned + `latest` on tags)
- `dependabot.yml` + `dependabot-auto-merge.yml` — weekly action/uv updates, patch updates auto-merged

## Before pushing

1. Review your own diff locally first.
2. Run the full test suite (`uv run pytest`), not just the tests near your change.
3. Work on a branch + PR, not direct commits to `master`.
