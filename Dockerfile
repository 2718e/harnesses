# dsh runs in a container as a security mitigation (see SAFETY.md in
# deepseek-harness). Base image is python:3.13-slim so the container carries
# the same Python major.minor as the host (3.13).

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

# pnpm is required for `dsh plugin` management. Version pinned for reproducibility;
# bump it here and rebuild to update.
RUN npm install -g pnpm @deepseek-ai/dsh@0.1.1-rc.2

# Non-root user matching host uid/gid 1000 so files written to the mounted
# workspace are owned by the host user. Home lives on the $DSH_HOME volume.
RUN groupadd --gid 1000 dev \
    && useradd --uid 1000 --gid dev --create-home --home-dir /dsh-home --shell /bin/bash dev

ENV DSH_HOME=/dsh-home
ENV HOME=/dsh-home
ENV DSH_TELEMETRY_MODE=DISABLED

# The web profile's HMR service requires the --expose-internals Node flag, which
# is not allowed via NODE_OPTIONS, so dsh is launched through this wrapper.
RUN printf '#!/bin/sh\nexec node --expose-internals /usr/local/lib/node_modules/@deepseek-ai/dsh/lib/bin.js "$@"\n' \
        > /usr/local/bin/dsh-prod \
    && chmod +x /usr/local/bin/dsh-prod

RUN mkdir -p /workspace && chown -R dev:dev /workspace

USER dev
WORKDIR /workspace

EXPOSE 3080

CMD ["dsh-prod", "web", "--no-open", "--trusted-host", "localhost", "--trusted-host", "127.0.0.1"]
