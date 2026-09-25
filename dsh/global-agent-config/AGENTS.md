# Global Behavior Constraints

- NEVER modify or append to the root `README.md` file.

## Feature documentation

When documenting or explaining features that you build, do so under `.agent-diaries/feature-docs/${date in YYYY-MM-DD}-${feature name}.md` (If the `.agent-diaries folder does not exist, create it)

## Your environment

Note that your home directory is read only. This is by design to keep your setup reproducible

## Python environments

- Use `uv` for all Python work: `uv sync`, `uv run <cmd>`, `uv add <pkg>`,
  `uv lock`, `uvx <tool>`. It is installed in the container.
- **Never create, activate, modify or delete a `.venv` directory.** A `.venv`
  may belong to the host (the container and host use different Python
  interpreters, so sharing one breaks it). The container's uv is configured with
  `UV_PROJECT_ENVIRONMENT=.venv-agent-container`, so `uv` commands automatically
  use the project-local `.venv-agent-container` instead and leave `.venv` alone.
- If you ever need to create an environment without uv, use
  `python -m venv .venv-agent-container` — never `.venv`.
- Add `.venv-agent-container/` to the project's `.gitignore` if it is not
  already there.

## Coding style

These are rules of thumb. Follow them if there is no specific reason not to, but these can be overriden by 

### Readability

When naming variables, functions, parameters, classes, interfaces, etc. choose names that match the plain-english intent of what the function is for.

Avoid excessive explanatory comments. Assume the user knows how to read code or can ask for explanations. Only use comments when something is counterintuitive.

Prefer to solve problems in the simple way, without writing more code than is mecessary to solve the problem. Less text and less code is easier to read.