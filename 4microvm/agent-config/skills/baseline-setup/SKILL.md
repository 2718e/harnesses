---
name: baseline-setup
description: Set up a verification command for a Python or TypeScript project, reusing existing tooling and installing missing checks.
---

# Project verification setup

Produce one working, documented verification command for the selected project.

## Inspect and fill gaps

Identify the project root, language, existing tooling, and workspace configuration.
A repository can contain several projects; configure the requested project rather
than creating a repository-wide aggregate command. The language must already be
chosen; application scaffolding is separate.

Ensure these categories are installed, configured, and included in verification:

- formatting checks;
- linting;
- static type checking;
- test discovery and execution;
- package manager.

Reuse suitable existing tools, package managers, configuration, and command
conventions. Add missing tools as development dependencies, respecting workspace
ownership and lockfiles. Preserve custom configuration and make reruns safe.

Use these defaults only where a choice is missing:

| Language | Package manager | Formatting/linting | Types | Tests |
| --- | --- | --- | --- | --- |
| Python | uv | Ruff | ty | pytest |
| TypeScript | pnpm | Prettier / ESLint with typescript-eslint | TypeScript | Vitest |

When introducing type checking, enable the checker's strict mode or its closest supported approximation. 
Preserve existing type-check
policy rather than migrating it during setup.

## Connect verification

Create or extend the project's check command to run these categories over its
source and relevant existing tests. Adapt to the project's layout and framework;
check formatting without rewriting files and propagate failures.

If no tests exist, write one clearly labelled infrastructure smoke test exercising
discovery, execution, and assertions. This is not application test coverage; do
not add further coverage as part of setup.

Run the command and report results. Existing failures are adoption work: do not
silently weaken checks or expand setup into broad code cleanup.

Document the command, working directory, prerequisites, and any smoke-only test
status in existing project documentation. Keep any agent guidance short and
operational. Report remaining failures and limitations.

Automatic review policy, CI generation, dependency auditing, and architecture
rules are separate work.
