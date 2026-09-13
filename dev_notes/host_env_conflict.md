## Problem description

Running things on host manually and agents running things inside the container makes the .venv conflict

## Solution idea

Configure the container so that uv will use system python inside the container (or create venvs somewhere outside the project folder)

Gemini suggested setting UV_PROJECT_ENVIRONMENT=/some/path or UV_SYSTEM_PYTHON=1 in Dockerfile.
