# Agent Python venvs via uv in the dsh container

Date: 2026-09-19

## Problem

The container and the host have different Python interpreters (host: Debian
`/usr/bin/python3.13`; container: python.org `/usr/local/bin/python3.13`), so a
shared `.venv` cannot work for both. Worse, uv treats an incompatible `.venv` as
stale and **deletes and recreates it**, so running the agent inside the container
silently destroyed a host-built `.venv` in the mounted project.

## Fix (option B)

Give the agent its own project-local environment and leave `.venv` alone:

- Install `uv` from the official image (pinned):
  ```dockerfile
  COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /usr/local/bin/
  ```
- Configure uv so every project environment goes to a container-only directory:
  ```dockerfile
  ENV UV_PROJECT_ENVIRONMENT=.venv-agent-container
  ENV UV_LINK_MODE=copy
  ```
  Relative `UV_PROJECT_ENVIRONMENT` resolves from the project root, so each
  project gets its own `.venv-agent-container`; `.venv` is never touched.
- `UV_LINK_MODE=copy`: uv's cache is on the writable `dsh-home` volume while the
  projects are host bind mounts (different filesystems), so hardlinking would
  fall back with a warning; copy makes it explicit.
- Agent-facing rules added to `global-agent-config/AGENTS.md`: use `uv`, never
  create/modify/delete `.venv`, use `.venv-agent-container` if creating an
  environment manually, and gitignore it.
- `dsh/README.md` note updated.

System-Python (`UV_SYSTEM_PYTHON=1`) was rejected: the rootfs is read-only, so
installing into `/usr/local/lib/python3.13/site-packages` fails with
`Read-only file system` (see [uv #13107](https://github.com/astral-sh/uv/issues/13107)),
and it also removes per-project isolation.

## Verification performed

In a scratch project (uv 0.12.17) with the exact env vars and a simulated
host-built `.venv` (`home = /usr/bin`, `version = 3.13.5`):

- `uv sync` created `.venv-agent-container` and left `.venv` and its marker file
  completely untouched.
- `uv run pytest` passed and ran from
  `<project>/.venv-agent-container/bin/python`; `python-dotenv` imported.
- Confirmed earlier that without the override uv *removes* the incompatible
  `.venv` (`Removed virtual environment at: .venv`), which this prevents.

The `ghcr.io/astral-sh/uv:0.12.17` tag was confirmed to exist via the GHCR
registry API. The Dockerfile was parsed with `dockerfile-parse`.

## Notes / follow-ups

- uv-managed Pythons (if a project needs a version other than 3.13) are
  downloaded under `$HOME/.local/share/uv/python` on the `dsh-home` volume and
  persist across recreates.
- `.venv-agent-container/` should be added to each mounted project's
  `.gitignore`; uv only auto-ignores `.venv`, so the agent instruction covers it.
- The agent only gets `uv` after the image is rebuilt and the container recreated
  (`just recreate`).
