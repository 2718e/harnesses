# Global Behavior Constraints

- NEVER modify or append to the any `README.md` files.

## Documentation

the primary place for agent written documententation is `.agent-writing/docs/MAIN.md` - this is what you should write to instead of writing to README.md files. If the MAIN.md gets long or complex, you can split it up into multiple files also under the `.agent-writing/docs` folder. A good rule of thumb for when to split out sections is when a documentaion file becomes more than 250 lines.

Write documentation in a concise way - it is generally easier for a human reader to read less words.

You can also make notes under `.agent-writing/diaries/${date in YYYY-MM-DD}-${feature name}.md`. This is for notes, learnings, decisions, and reasoning behind decisions. files in `agent-writing/diaries` relate to **a point in time** - don't edit files in this folder if the datestamp on the file is not the current date. Don't waste tokens reading the diaries unless you want to understand historical reasoning about a past project decision.

If the `.agent-writing/docs` or `.agent-writing/diaries` folders don't exist create, them. If a project has an `.agent-diaries` folder (or an `.agent-diaries/feature-docs`), move the contents into `.agent-writing/diaries` then remove the folder.

### Handling monorepos

I sometimes have more than one project inside the same git repository. In these case the instructions about where to create documentation are relative to the root of each individual project, not the repository or workspace.

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

### Readability

When naming variables, functions, parameters, classes, interfaces, etc. choose names that match the plain-english intent.

Avoid excessive explanatory comments. Assume the user knows how to read code. Only use comments when something is counterintuitive, and keep the comments as concise as possible.

Prefer to solve problems in the simple way, without writing more code than is necessary to solve the problem. Less text and less code is easier to read.

### Exensibility and composability

Rules of thumb:

Objects and functions should depend on abstractions (e.g. interfaces, or similar constructs depending on implementation language)

DI / IOC Pattern: Objects and functions should expect to be passed fully constructed dependencies and inputs rather than internally constructing them. Some caveats: 
- It is OK to create convenience methods that construct the dependencies and then pass them to the method that accepts the dependencies.

### Type safety

In languages with optional typing features, these typing features should be used. 

## Security

Follow these rules in addition to any you already would:

- do not add secrets (such as API keys) or identifying information (such as email addresses or phone numbers) to source controlled files.