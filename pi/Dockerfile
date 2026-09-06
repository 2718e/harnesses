# Pi harness has no built-in guardrails or permission system, so it runs in a
# container as the security boundary (same rationale as the dsh setup).

FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        git \
        build-essential \
    && curl -fsSL https://nodejs.org/dist/v24.13.0/node-v24.13.0-linux-x64.tar.xz \
        | tar -xJ -C /usr/local --strip-components=1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Non-root user matching host uid/gid 1000 so files written to mounted
# workspaces are owned by the host user. Home lives on the $HOME volume
# (pi-home in compose.yaml); it is seeded from /pi-home in the image on first
# start, then persists across container recreates.
RUN groupadd --gid 1000 dev \
    && useradd --uid 1000 --gid dev --create-home --home-dir /pi-home --shell /bin/bash dev

ENV HOME=/pi-home
# Pi: skip the pi.dev update check and opt out of install/update telemetry.
ENV PI_SKIP_VERSION_CHECK=1
ENV PI_TELEMETRY=0

# The Pi harness and its plugins are ordinary npm dependencies of this project
# (package.json / package-lock.json), so they are installed with `npm ci`
# during the build instead of being pinned in this Dockerfile. Bump versions in
# package.json, regenerate the lockfile, and rebuild to update.
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
ENV PATH="/app/node_modules/.bin:${PATH}"

# Seed the Pi agent home (see home/.pi/agent/settings.json: it registers the
# web search extension from /app/node_modules). A fresh named volume gets this
# content copied in automatically on first start.
COPY home/. /pi-home/
RUN chown -R dev:dev /pi-home

RUN mkdir -p /workspace && chown -R dev:dev /workspace

USER dev
WORKDIR /workspace

# Keep the container running; open an interactive Pi session with:
#   docker compose exec -it pi pi
CMD ["sleep", "infinity"]
