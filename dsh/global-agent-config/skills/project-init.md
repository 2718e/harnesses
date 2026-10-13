---
name: project-init
description: Will be called by the user in order to set up the structure for a new project.
disable-model-invocation: true
---

Initialise a new project based on instructions given.

Here are some defaults that can be used unless the user instructions contradict it.

## Running convenience

Make a justfile for putting common commands the user might want to use e.g. run the thing, run the tests

## Default tech choice

Here are my default tech choices for different types of project

Backend projects:

- Python as language choice
- UV as package manager
- FastAPI if a web server is needed
- pytest

Frontend projects:

- React, typescript, vite (and vitest).
- pnpm for package management

General rule, if there is a strong de-facto standard for a particular project type, follow the de-facto standard

