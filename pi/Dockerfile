# Pi harness does not have built in guardrails. Run in a container as a precaution

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

RUN mkdir -p /workspace && chown -R dev:dev /workspace

USER dev
WORKDIR /workspace

EXPOSE 3080
