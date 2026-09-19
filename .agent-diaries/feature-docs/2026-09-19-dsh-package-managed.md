# dsh version managed by package.json

Date: 2026-09-19

## What

`@deepseek-ai/dsh` is no longer installed from a version pinned in the
`Dockerfile`. It is now an ordinary dependency of the `dsh/` node project
(`package.json` + `pnpm-lock.yaml`), installed with pnpm during the image build,
mirroring how the `pi/` harness pins its agent.

## Changes

- `dsh/package.json` (new): private project, exact pin
  `"@deepseek-ai/dsh": "0.1.5-rc.2"`.
- `dsh/pnpm-lock.yaml` (new): generated with pnpm 12.4.2 (`pnpm install
  --lockfile-only`).
- `dsh/Dockerfile`:
  - `RUN npm install -g pnpm@12.4.2` — npm installs only the package manager.
  - `WORKDIR /app` + `COPY package.json pnpm-lock.yaml` +
    `pnpm install --frozen-lockfile --ignore-scripts --store-dir /tmp/pnpm-store`
    then `rm -rf /tmp/pnpm-store`.
  - `ENV PATH="/app/node_modules/.bin:${PATH}"`.
  - `dsh-prod` wrapper now points at
    `/app/node_modules/@deepseek-ai/dsh/lib/bin.js`.
- `dsh/.dockerignore` (new): keeps `.env`, `node_modules`, compose/spec/agent
  files and `.git` out of the build context.
- `dsh/README.md`: package-manager / "Updating dsh" notes.

## Why npm still appears once

`pnpm` is a runtime requirement (`dsh plugin` forwards to pnpm and profile boot
manages the profile's pnpm project), so it must be on PATH regardless. The only
reason npm is involved at all is to bootstrap pnpm itself; every project
dependency is installed by pnpm. Corepack (the npm-free alternative) was
considered and rejected to avoid depending on a deprecated Node feature.

## Notes / gotchas

- Commit `pnpm-lock.yaml`; the build uses `--frozen-lockfile`. To bump: edit
  `package.json`, run `pnpm install`, rebuild.
- `--ignore-scripts` is safe: native pieces (node-pty, sharp, koffi, ...) ship
  prebuilt binaries; no dependency needs an install script.
- The build-time pnpm store (258 MB) is deleted after install. pnpm hardlinks
  packages into `node_modules/.pnpm`, so removing the store leaves a working
  tree (verified: `dsh --version` and `--profile web --dump-config` still run).
- `node_modules/@deepseek-ai/dsh` is a symlink into `.pnpm/...`; the wrapper's
  absolute path resolves through it.
- Runtime pnpm (`dsh plugin`) operates in `$DSH_HOME/profiles/...` on the
  writable `dsh-home` volume, so its store never lands on the read-only rootfs.

## Verification performed

- `pnpm install --frozen-lockfile --ignore-scripts` from the committed files,
  then `dsh --version` → `0.1.5-rc.2` and `--profile web --dump-config` → 539
  lines, byte-identical to the previously global install.
