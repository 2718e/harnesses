# Baseline agent development environment

## Purpose and scope

Turn the recommendations in `plan_references/agentic-coding-deep-research-report.md`
into a small, reusable baseline for projects used by the harnesses in
`4microvm/`.

The VM makes capabilities available. Individual projects adopt tooling and
workflow policies. Do not install universal development/review policy in the
VM's harness-level or user-level instructions.

Initial language support: Python and TypeScript. Add Rust when there is an
actual Rust project. The old top-level `dsh/` setup and decisions about reusing
its contents are outside this work.

Keep the baseline grounded in the research's practical recommendations.
More specific or complex flows can be added later.

## Agreed responsibilities

### Standalone review skill

Provide a reusable review capability with a name that avoids collisions with
built-in harness commands (working name: `baseline-review`).

A human can invoke it directly, or an agent can use it as a reviewer subagent.
It reviews a specified change and returns findings. It does not decide when
reviews happen, implement fixes, or own a review/fix loop.

Automatic triggers and review requirements belong to project policy or a
separate orchestration workflow.

### Project baseline setup

The output of setup is a working, documented verification command for a project.
Installing and configuring missing tools is part of producing that command.

Setup differs from initialisation:

- Initialisation chooses a starting stack and scaffolds a project, saving the
  user from making each tool choice.
- Baseline setup examines a project whose language is already defined and
  ensures verification categories are covered. Reuse suitable existing tools;
  choose defaults only for missing categories.

A project is not necessarily a repository. A repository can have a Python
backend and TypeScript frontend, each with its own tooling and verification
command. Account for workspace-managed dependencies and shared configuration.

Setup must:

- Identify the target project, its language, and relevant existing tooling.
- Ensure formatting checks, linting, type checking, and a test runner are
  installed and configured. Python includes a separate type checker.
- Reuse suitable existing tools and command conventions.
- Expose one documented verification command for that project.
- Run verification and accurately report failures or missing verification.
- Keep any project instructions short and operational. Preserve existing
  instructions and avoid duplicate content on reruns.

Adding missing application test coverage is outside setup. If no tests exist,
add one clearly labelled infrastructure smoke/example test to demonstrate that
discovery, execution, and assertions work. This can make verification pass, but
does not establish application behaviour. Report the distinction explicitly.
Do not add another example when tests already exist.

Proposed boundary: broad formatting, typing, and lint cleanup of existing code
is separate work. Report problems exposed by new checks rather than silently
weakening checks or expanding setup into a general cleanup.

### Separate build/review/fix orchestration

A separate skill or invocation method can implement a build with automatic
review and fixes. It composes the standalone review capability.

The cycle has a configurable maximum with a sensible default. Projects can
choose this workflow as their default way to build or define automatic triggers.
Installing review or running setup does not itself opt a project into it.

Include this in the first draft as a separate skill, `baseline-build`, with a
default maximum of three review passes and a configurable positive integer limit.
Each reviewer invocation consumes a pass, including an incomplete attempt.
After final-pass fixes, run verification and report that those edits have not
had another independent review. Reaching the limit does not establish success.

## Proposed details to refine

The draft below makes concrete choices for inspection and revision. These have
not been validated through provisioning or acceptance testing.

### Verification

- Check formatting without rewriting files; provide fixes separately.
- Run language checks and configured tests; propagate failures.
- With no tests, add one infrastructure smoke test. Verification may pass while
  documentation and setup reporting explicitly state that the suite is smoke-only.
- Leave dependency-audit configuration unchanged in this first draft; keep future
  network-dependent audits separate from fast checks.
- Do not create repository-level aggregate commands yet. Their form is deferred.
- Add architecture checks when there is a concrete boundary to protect.

### Review contract

- Accept explicit change scope: a base revision or specified working-tree
  changes, including relevant untracked files.
- Review against requirements, surrounding code, and verification results,
  rather than relying exclusively on the diff or implementer's explanation.
- When orchestrated, use a fresh reviewer context. Do not claim independent
  review when the harness cannot provide it.
- Inspect without modifying the implementation; return actionable findings with
  locations, consequences, and supporting evidence.
- Report verification limitations and distinguish reviewer failure from no
  actionable findings.
- Cover correctness, regressions, meaningful missing behavioural tests, trust
  boundaries, and concrete maintainability problems.

Naming guidance: assess semantic clarity across symbols, files, and modules in
context. Flag misleading names or names that materially obscure behaviour,
units, ownership, or side effects. Respect conventions and compatibility costs;
avoid unrelated renaming and subjective synonym preferences.

### Cycle semantics

- Build, verify, obtain a fresh review, evaluate findings, fix justified issues,
  and rerun affected checks.
- Define what counts as a cycle and when another review is needed.
- Bound iterations. At the limit, report unresolved findings and failed checks;
  reaching the limit is not successful completion.
- Do not require accepting every reviewer suggestion.

### VM delivery

- Store shared skill content under `4microvm/agent-config/`, with harness-specific
  integration where needed.
- Make capabilities available during provisioning without universal triggers.
- Verify skill discovery and fresh reviewer invocation against pinned harness
  versions. Shared prose alone does not establish working delegation.

## First draft contents

Source lives under `4microvm/agent-config/skills/`:

- `baseline-setup/SKILL.md`: project-scoped tooling inspection, gap filling, and
  verification command setup. Language references define fallback choices;
  assets provide adaptable shell check scripts and infrastructure smoke tests.
- `baseline-review/SKILL.md`: concise review checklist with optional scope and
  intended behaviour, usable directly or by a delegated reviewer. Inferred
  expectations supplement supplied intent. Default working-tree scope includes
  staged and unstaged changes, without automatically including untracked files.
- `baseline-build/SKILL.md`: concise bounded build/verify/review/fix workflow,
  managed by the builder.
- `baseline-build-coordinator/SKILL.md`: alternative with a light coordinator
  delegating implementation and fixes to a builder and review to a fresh reviewer.

The two build variants are alternatives for comparison, not nested workflows.
Both use the same three-pass default and reviewer context boundary. The earlier
detailed handoff reference has been removed; role, scope, and iteration details
now live in the concise skill bodies. Earlier proposed report fields and detailed
procedures above are not requirements imposed by these minimal drafts.

Fallback choices for inspection: Python uses Ruff, mypy, and pytest; TypeScript
uses Prettier, ESLint with typescript-eslint, TypeScript, and Vitest. Preserve
suitable existing tools and settings. References describe initial strictness
and integration choices; these are editable draft defaults.

The draft does not change provisioning, install skills into a running harness,
or implement harness-specific CLI delegation adapters. Skills describe the
required integration and report unavailable delegation instead of pretending
self-review is independent review. Provisioning and testing come later.

## Deferred work

- Inspect the actual draft skills, scripts, defaults, and report/cycle semantics.
- Wire skill discovery and fresh reviewer invocation for each pinned harness.
- Provision and exercise the setup and workflows, then evaluate acceptance.
- Design repository-wide aggregate commands separately.

## Initial acceptance criteria

- Review works manually and as a reviewer subagent without imposing triggers or
  running its own fix loop.
- Setup adds missing tools and documented verification commands to Python and
  TypeScript projects.
- Suitable existing tools and custom configuration survive setup and reruns.
- A Python backend and TypeScript frontend in one repository can be configured
  separately without conflicting with each other's tooling.
- No-test projects receive only an infrastructure smoke test; smoke-only status
  and existing failures are reported honestly without silently relaxing checks.
- Both installed harnesses discover the skills in a freshly provisioned VM.
- Orchestration respects its limit and reports unresolved work without claiming
  success.

These criteria are for later validation, not claims established by this draft.
