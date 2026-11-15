# Evidence-based practices for high-quality agentic software development

## Executive synthesis

The strongest conclusion from the evidence available through **2 November 2026** is that high-quality agentic development is less about finding a perfect prompt and more about constructing an environment in which mistakes are **cheap to expose, difficult to preserve, and easy to localise**. Traditional software-engineering mechanisms such as information hiding, automated testing, type checking, dependency control, reproducible environments and version control remain relevant because they constrain the *state of the software*, rather than relying on either a human or an agent to remember every desirable property. Parnas's original argument for information hiding was explicitly about making systems easier to change and comprehend by hiding design decisions likely to change; decades of empirical work subsequently found associations between lower coupling/higher cohesion and fault or maintenance outcomes, although static structural metrics are imperfect proxies for actual future maintainability. citeturn636135search0turn636135search4turn636135search7

That distinction between **enforced state** and **instructions** has become especially important with coding agents. A 2026 controlled study of repository-level `AGENTS.md`-style context files found that such files did not improve task success across the tested agents and models and increased inference cost by more than 20%; the authors found that agents generally obeyed the instructions, but unnecessary requirements induced extra exploration and work. A separate two-agent ablation study likewise found no measurable correctness improvement from repository context files on its smaller real-repository task set. The appropriate response is not to abandon project instructions, but to keep them *minimal*: commands, non-obvious constraints, architectural boundaries and operational facts that cannot be discovered cheaply from the repository itself. citeturn973383academia7turn381654search3

The corresponding positive finding is that **verification beats exhortation**. A large October 2026 study comparing 17 verification designs across seven frontier coding models found independent critic review produced gains of roughly 5.9–9.5 percentage points on Terminal-Bench and 3.9–6.6 points on SWE-bench Verified at relatively modest incremental inference cost, while completion gates could help more but were often substantially more expensive. This supports a workflow in which the implementation agent is allowed to work freely inside a constrained environment, deterministic checks run automatically, and an independent review pass is reserved for non-trivial changes rather than adding ever more prose to the initial prompt. citeturn973383academia6

Testing is particularly important because the best current evidence on *longitudinal* agent maintenance suggests that preserving behaviour matters more than whether code was authored by a human or an agent. SWE-Maintain, published in October 2026, compared later maintenance from developer-written versus agent-written histories across 1,996 paired events. Agent-history reduced later-task resolution by 5.6 percentage points overall and by 14 points when all accumulated tests also had to pass, but when the inherited agent state already passed earlier tests the apparent maintenance disadvantage disappeared within statistical uncertainty: +2.7 points, 95% CI −0.5 to +6.1. Two-thirds of agent-history states in the study already failed earlier tests. That is unusually actionable evidence: **do not allow a change that breaks established behaviour to become the starting point for the next change**. citeturn973383academia9

A second 2026 maintenance benchmark, CodeThread, found task-resolution drops of up to 13.1% when agents subsequently modified agent-produced rather than human-produced code. Traditional maintainability metrics did not explain much of the difference; error handling, input validation, downstream code size and task-specific characteristics were more informative. Taken together with SWE-Maintain, the evidence does **not** support the broad claim that agent-written code is intrinsically unmaintainable. It supports the narrower claim that agent changes can leave behavioural defects or subtle design liabilities which compound if they are not caught immediately, and that common static maintainability metrics alone are inadequate safeguards. citeturn973383academia8turn973383search2

Security deserves separate treatment. SUSVIBES, an ICML 2026 benchmark built from 186 real-world feature requests with known vulnerable human implementations, tested 12 agentic settings. With SWE-Agent plus Claude 4 Sonnet, 57% of attempted solutions were functionally correct but only 11.8% were secure under the benchmark's criteria; adding vulnerability hints to the prompt did not resolve the problem. This is strong evidence against relying on "remember security" instructions. Security should instead be supported by dependency auditing, static analysis, permissions, sandboxing, secret isolation and explicit testing at trust boundaries. citeturn704345search5

Agents' ability to navigate repositories also remains imperfect. ContextBench contains 1,136 issue-resolution tasks across 66 repositories and eight languages; its 2026 evaluations found that sophisticated scaffolding only marginally improved context retrieval and that agents tended to retrieve broadly while using only a subset of what they explored. Agent Retrieval Bench independently found no universally best retrieval method: embedding retrieval led some metrics, while repository maps achieved the best gold-file yield under an 8K-token budget; logged agent trajectories missed every gold file on roughly 27–35% of samples. Consequently, a baseline environment should make discovery easy through normal software artefacts—clear module boundaries, searchable names, type information, tests and dependency structure—rather than attempting to pre-load a complete architectural description into context. citeturn381654academia10turn381654search1

The broader productivity evidence argues for measuring **total human effort**, as the brief requests, rather than assuming that more agent autonomy always saves time. METR's randomised controlled trial with 16 experienced open-source developers performing 246 tasks in projects they knew well found early-2025 AI tools increased completion time by 19%, even though developers expected them to save time. The study mostly used Cursor with Claude 3.5/3.7 Sonnet, so it should not be extrapolated directly to late-2026 agents; its continuing relevance is methodological: perceived productivity and benchmark scores can diverge materially from actual task time. citeturn704345search7

Finally, benchmark results themselves need care. SWE-bench was a major advance because it evaluates real repository changes rather than isolated functions, but OpenAI stopped reporting SWE-bench Verified in February 2026 after finding substantial evidence of training contamination among frontier models and recommended newer evaluations such as SWE-bench Pro. SWE-rebench similarly demonstrated why continuously refreshed tasks are valuable. For evaluating a personal agentic-development setup, a private sequence of real changes to repositories you control will now be more decision-relevant than chasing a public leaderboard. citeturn704345search0turn704345search1turn704345search6

For a technically proficient solo developer, this points to a relatively small baseline:

1. **Use strong language-native checks and tests, and make one fast `check` command authoritative.**
2. **Never accept a change while previously passing behavioural tests fail.**
3. **Keep persistent agent instructions short and operational, not encyclopaedic.**
4. **Use git commits or worktrees as cheap checkpoints and isolate consequential changes.**
5. **Automate formatting, types, linting, tests, dependency/security checks and only a few architecture rules that protect real boundaries.**
6. **Run an independent agent review for non-trivial changes, then require deterministic checks again after fixes.**
7. **Use a reproducible, permission-limited execution environment and keep credentials unavailable unless a task genuinely requires them.**
8. **Measure success over sequences of changes, including human intervention time—not merely first-pass completion.**

The principal unresolved question is no longer whether agents can solve useful coding tasks—they clearly can—but which development structures produce the best **multi-iteration** outcomes with late-2026 models. Longitudinal benchmarks such as CodeThread, SWE-CI and SWE-Maintain are only now beginning to measure that directly. SWE-CI, for example, models repository evolution over tasks whose histories average 233 days and 71 commits, whereas the older single-issue paradigm largely measures a fresh start from human-maintained code. citeturn661920academia8turn973383academia8turn973383academia9

## Engineering principles that survive the transition to agents

### Information hiding, cohesion and coupling

The most useful conventional principle is **not** "make everything modular"; it is "localise decisions that are likely to change". Parnas's 1972 comparison showed why decomposing by processing steps can expose many modules to one changing decision, whereas decomposing around hidden design decisions can confine change. This is primarily a theoretical/design argument rather than a modern controlled experiment, but subsequent empirical studies have repeatedly found relationships between coupling/cohesion measures and faults or maintenance activity. At the same time, a longitudinal study of 233 releases across ten systems found that aggressively optimising cohesion/coupling would often be highly disruptive—about 57% of structure would need to change—whereas developers appeared to accept more modest structural improvements. citeturn636135search0turn636135search5

For agentic development, the practical translation is **stable seams around volatile concerns**: external APIs, persistence, file formats, third-party services, operating-system interaction and domain policies likely to change. An interface is valuable when it creates a real replacement boundary; an extra class, wrapper or "service" that simply forwards calls is not. The evidence gives no reason to maximise abstraction count, and CodeThread's finding that conventional metrics did not explain agent-maintenance outcomes is a warning against optimising for low coupling scores as an objective in itself. citeturn973383academia8

A useful default for small projects is therefore a **modular monolith** rather than either a single undifferentiated directory or a microservice architecture: cohesive feature or domain modules, explicit adapters for unstable external dependencies, and dependencies flowing in a small number of predictable directions. This recommendation is a pragmatic inference from information-hiding theory, empirical coupling research and the overhead constraint in the brief; it is not supported by an agent-specific experiment proving that "modular monolith" is optimal. citeturn636135search0turn636135search5

### Readability and understandability

Human readability has measurable effects, but many style preferences have weaker evidence than engineering folklore suggests. An experiment with 88 Java developers found descriptive compound identifiers led participants to locate semantic defects about 14% faster than shorter names, while making no corresponding difference for syntax-error detection. A 2023 systematic review of formatting experiments found statistically significant effects for several formatting choices, but also divergent or inconclusive findings, including conflicting results for camelCase versus snake_case. citeturn636135search8turn636135search9

The rational baseline is therefore **semantic clarity plus mechanical formatting**, not a lengthy style guide. Names should expose intent, unusual invariants should be explicit, and source layout should be standardised automatically. Debates about quote style, brace placement or equivalent formatting conventions should generally be delegated to the formatter because the empirical evidence does not justify human or agent attention being spent repeatedly on them. citeturn636135search9

There is little direct evidence that late-2026 coding agents benefit from precisely the same naming conventions as humans. However, agents must search text, retrieve symbols and reason across references, and current context-retrieval benchmarks demonstrate that locating relevant files remains a bottleneck. Descriptive names and conventional source organisation therefore have a plausible agent benefit in addition to their demonstrated human benefit, but this transfer should be labelled **plausible rather than proven**. citeturn381654academia10turn381654search1

### Types, tests and executable specification

Static types and tests catch different classes of defect. For the three target languages, the language ecosystems already provide low-cost native checks: TypeScript's `strict` option enables its family of stricter checks, with `noUncheckedIndexedAccess` additionally treating unverified indexed access more conservatively; Python can pair a static checker with normal runtime tests; Rust integrates compile-time checking with Clippy and `cargo test`. citeturn696402search0turn696402search43turn696402search1

The important agent-specific point is to treat tests as **accumulated behavioural memory**. A test is valuable not merely because the implementation agent can use it while fixing today's task, but because it prevents tomorrow's agent from silently invalidating yesterday's requirement. SWE-Maintain supplies unusually direct empirical support for this interpretation. citeturn973383academia9

This does **not** imply mandatory TDD. A systematic review of 27 TDD studies reported quality improvements in many studies but mixed productivity results; an earlier meta-analysis found a small overall positive effect on external quality with little overall productivity effect, with substantial variation by setting. More recent agent research also cautions against equating "the agent wrote more tests" with better outcomes: a 2026 analysis of six strong models found that changing test-writing volume through prompting did not significantly change final SWE-bench outcomes in its setting. citeturn636135search10turn636135search11turn381654search5

The baseline should therefore require **tests for externally observable behaviour and regressions**, not a ritualised test-first process. When requirements are exploratory, it is reasonable to implement a spike, learn from it, then turn the discovered behaviour that matters into tests before treating the capability as stable.

### Security and robustness

Security engineering especially rewards enforced controls. SUSVIBES shows that functional correctness and security correctness can diverge dramatically in agent-written solutions, and that adding a prompt hint is insufficient. The baseline should assume the agent will occasionally omit validation, mishandle a permission boundary or select an unsafe library pattern and should use independent mechanisms to detect or contain the result. citeturn704345search5

For Rust, `cargo-deny` can enforce dependency advisories, licence rules, banned crates and source policies. CodeQL supports JavaScript/TypeScript, Python and Rust, and Semgrep supports all three languages as well. These tools are not proof of security: static analysers have both false positives and false negatives and are strongest for vulnerability classes they model well. Their value is that they turn some security expectations into repeatable checks rather than conversational suggestions. citeturn470779search2turn696402search10turn696402search6

Execution isolation is equally important because an agent is not merely generating text: it may execute repository scripts, package installers and tests. Dev Containers provide a version-controlled specification for development environments, and current agent harnesses increasingly expose explicit sandbox or permission controls. A container is not by itself a perfect security boundary, but a disposable environment with minimal credentials, restricted mounts and limited network or host access sharply reduces the consequence of a mistaken command compared with unrestricted execution on a user's primary machine. citeturn470779search1turn685221search0turn685221search7

## What current coding agents actually do well and poorly

The capability picture has changed rapidly enough that results must be tied to dates and model generations. The original SWE-agent NeurIPS 2024 system, built around an agent-computer interface for repository navigation, editing and execution, achieved only 12.5% on the then-current SWE-bench evaluation while dramatically outperforming non-interactive baselines. By 2025–26, public leaderboard scores on some SWE-bench variants had risen far enough that benchmark contamination itself became a major concern. This means conclusions based on GPT-4-era or Claude-3-era failure rates should not be used as estimates of 2026 frontier capability. citeturn381654search6turn704345search1

Nevertheless, harder and more realistic tasks remain unsolved at high rates. SWE-Lancer contains more than 1,400 real freelance engineering tasks worth an aggregate $1 million and found the evaluated frontier systems unable to solve the majority. RExBench asked agents to implement research extensions across twelve research codebases; its best tested agent succeeded on about 31% without additional human-written hints and below 48% with them. These evaluations indicate that long-horizon integration and underspecified feature work remain substantially harder than local bug repair. citeturn704345search4turn661920search4

Repository context is a persistent weakness. ContextBench's best current systems can have high end-to-end pass rates on its task mixture while still showing low context F1, and Agent Retrieval Bench found that neither embeddings, lexical search nor repository maps dominated all retrieval tasks. This argues for exposing multiple cheap exploration mechanisms—text search, symbol search, compiler/type information, tests and an import graph—rather than investing heavily in a single bespoke RAG system for a small or medium repository. citeturn381654search9turn381654search1

Code quality after the first successful patch is now an empirically visible risk. CodeThread's up-to-13.1-point downstream resolution penalty and SWE-Maintain's accumulated-regression result both indicate that "passes today's acceptance test" is too weak a definition of success. Yet SWE-Maintain also gives an encouraging counter-result: when prior tested behaviour had been preserved, agent-authored history was not detectably harder to extend in that experiment. The highest-leverage intervention therefore appears to be protecting accumulated behaviour, not trying to force agent code to resemble human code stylistically. citeturn973383academia8turn973383academia9

The evidence on agent-produced code being inherently uglier or less understandable to humans is much weaker. Sawada et al.'s 2026 observational analysis of more than 1,000 files and around 3,200 changes found different maintenance patterns for agent-generated and human-authored files, but observational repository data cannot establish that authorship caused those differences. CodeThread's inability to explain maintenance outcomes with standard maintainability metrics also warns against using cyclomatic complexity, file length, coupling or an LLM "code quality score" as a substitute for actual modification experiments. citeturn661920academia6turn973383academia8

Independent review is one of the stronger agent-specific interventions discovered so far. The October 2026 verification study found better accuracy/cost trade-offs for an independent critic than for simply adding reminders or repeated completion checks. Independence matters conceptually because the reviewer receives an opportunity to form a separate hypothesis about defects rather than merely continuing the implementer's trajectory. This does not eliminate correlated model errors, especially when the same model family performs both roles, but it is currently better-supported than elaborate multi-agent debate or many-stage software-development role-play. citeturn973383academia6

## Evidence matrix: techniques and tooling

| Technique | Intended benefit and mechanism | Evidence and limitations | Cost / complexity | Recommendation |
|---|---|---|---|---|
| **Preserve all previously passing behavioural tests** | Prevents accumulated regressions from becoming the base state for later work. | SWE-Maintain directly found that inherited failures drove much of the later maintenance penalty; when prior tests passed, the agent-history disadvantage disappeared within uncertainty. Python-only episodes and two backbone models limit generalisation. citeturn973383academia9 | Low once tests exist; test-suite runtime can grow. | **Adopt now — strongest agent-specific recommendation.** |
| **Strict static typing where economical** | Detects inconsistent interfaces, invalid states and refactoring errors before execution. | Strong ecosystem support; direct late-2026 agent-maintainability effect is not well quantified. TypeScript `strict` and Rust compiler checks are particularly inexpensive to integrate. citeturn696402search0turn696402search1 | Low–moderate; Python annotation effort can be non-trivial. | **Adopt now**, especially at module boundaries. |
| **Automatic formatting and mainstream linting** | Removes stylistic variance and catches common defects without review effort. | Human formatting studies show some effects but many style questions are inconclusive; tools are cheap and deterministic. Ruff and Clippy consolidate many checks. citeturn636135search9turn696402search15turn696402search16 | Very low. | **Adopt now.** |
| **Descriptive, semantically meaningful names** | Improves human comprehension and searchability; plausibly assists agent retrieval. | Human experiment found ~14% faster semantic-defect discovery with descriptive identifiers; direct agent effect remains uncertain. citeturn636135search8 | Very low. | **Adopt now**, without elaborate naming rules. |
| **Information-hiding boundaries around volatile concerns** | Localises future change and reduces ripple effects. | Classic design argument plus empirical coupling/maintenance evidence; not an agent-specific RCT. Aggressive remodularisation can itself be disruptive. citeturn636135search0turn636135search5 | Low if introduced when a real seam appears; high if overengineered. | **Adopt selectively.** |
| **Persistent `AGENTS.md` / `CLAUDE.md`-style instructions** | Supplies durable commands, constraints and project knowledge. | 2026 controlled evidence found no average success improvement from fuller context files and >20% inference-cost increase; smaller ablation similarly found little correctness effect. citeturn973383academia7turn381654search3 | Low authoring cost but continuous context/token cost. | **Adopt only a minimal file. Avoid encyclopaedic instructions.** |
| **Repository map / structured code navigation** | Helps find relevant symbols and relationships under context limits. | Agent Retrieval Bench found RepoMap strongest on its 8K-token budget metric but not universally best; ContextBench finds retrieval remains difficult. citeturn381654search1turn381654academia10 | Low if harness-native; moderate for bespoke indexing. | **Optional now; useful for larger repos.** |
| **Independent agent review** | Provides a separate verification trajectory and defect search. | Seven-model 2026 study found 3.9–6.6 pp SWE and 5.9–9.5 pp Terminal-Bench improvements at relatively small incremental cost. SWE-bench contamination is a caveat. citeturn973383academia6turn704345search1 | One extra model call/trajectory. | **Adopt for non-trivial changes.** |
| **More initial planning / waterfall-style decomposition** | Attempts to prevent architectural mistakes before coding. | Evidence is mixed and task-dependent; exploratory development makes large upfront plans stale. MaintainCoder reports gains under its own benchmark, but its waterfall/design-pattern/multi-agent package does not isolate which component helped. citeturn661920search10 | Moderate–high. | **Do not mandate. Use short plans when cross-cutting change warrants them.** |
| **Agent-generated tests as a required ritual** | Provides executable specification and feedback. | Tests themselves are valuable, but a 2026 study found prompt-induced increases in agent-written test volume did not significantly alter final outcomes in its SWE-bench setting. citeturn381654search5 | Can be substantial. | **Require useful regression evidence, not test-count targets or universal TDD.** |
| **Architecture dependency checks** | Makes module boundaries machine-enforceable rather than advisory. | `dependency-cruiser` can forbid JS/TS dependency relationships and cycles; Import Linter provides Python forbidden/layer contracts. Evidence for tools is operational rather than controlled maintainability experiments. citeturn470779search3turn470779search0 | Low once a boundary genuinely matters. | **Optional baseline; adopt after the first meaningful architectural seam exists.** |
| **SAST / dependency analysis** | Detects known insecure patterns and vulnerable dependencies independently of prompting. | Strong motivation from SUSVIBES; CodeQL supports TS/JS, Python and Rust, while Semgrep covers all three. No scanner guarantees security. citeturn704345search5turn696402search10turn696402search6 | Low–moderate; false-positive triage is the main cost. | **Adopt a lightweight dependency scanner now; add SAST for internet-facing/high-risk projects.** |
| **Reproducible containerised development** | Reduces environment drift and confines execution. | Dev Container is a standard version-controlled environment format. Direct productivity evidence for solo agentic development is limited; benefits are operational and security-related. citeturn470779search1turn470779search5 | Moderate initial setup. | **Adopt where Docker is already acceptable; otherwise pin toolchains and lockfiles first.** |
| **Static maintainability scores as quality gates** | Attempts to predict future change cost from complexity/coupling/etc. | Traditional studies show correlations, but CodeThread found common maintainability metrics did not explain agent-code downstream performance. citeturn636135search7turn973383academia8 | Easy to calculate; risk of gaming/Goodhart effects. | **Avoid as hard gates. Use diagnostically at most.** |
| **Large multi-agent role hierarchies** | Adds planners, architects, testers, reviewers and managers. | Independent review has evidence; large role ensembles have far less clean evidence relative to added cost and correlated failure. Current benchmark results vary materially by harness. citeturn973383academia6turn661920search9 | High tokens, latency and orchestration complexity. | **Experiment, not baseline.** |

## Recommended minimal baseline environment

The guiding principle is **one repository, one canonical verification command, short persistent guidance, disposable execution, and increasing ceremony only when risk warrants it**.

### Repository organisation

A good reusable default is:

```text
project/
├── AGENTS.md
├── README.md
├── src/                    # or packages/, crates/, app/
│   ├── <domain-or-feature>/
│   ├── adapters/           # external APIs, storage, OS, network
│   └── ...
├── tests/
│   ├── integration/
│   └── ...
├── scripts/
│   └── check               # canonical verification entry point
├── docs/
│   └── decisions/          # only consequential decisions
├── .devcontainer/          # optional, recommended when useful
├── <language config>
└── lockfile
```

The exact folders matter less than three properties: a newcomer can find production code and tests quickly; external/volatile dependencies have recognisable seams; and there is a **single documented command** that reproduces the checks the agent must satisfy. This recommendation follows from information-hiding principles, context-retrieval weaknesses and the strong maintenance value of preserving previously tested behaviour. citeturn636135search0turn381654academia10turn973383academia9

Do not start with `interfaces/`, `services/`, `repositories/`, `factories/`, `managers/`, event buses and dependency injection merely because they might become useful. Introduce a boundary when two implementations actually need to vary, a dependency is unstable or difficult to test, or a domain rule benefits from isolation. The longitudinal cohesion/coupling evidence shows that structural improvement must be balanced against disruption; "more decomposition" is not a monotonic quality function. citeturn636135search5

### Persistent instructions

Keep the global/project instruction file to roughly the information an agent cannot reliably infer itself. A representative file is:

```markdown
# Repository guidance

## Verify
Run `./scripts/check` before declaring work complete.
Do not leave previously passing tests failing.
Do not weaken, delete or skip a test merely to make the suite pass.

## Design
Prefer the smallest change that satisfies the requirement.
Preserve existing public behaviour unless the task explicitly changes it.
Keep external I/O behind the existing adapter boundaries.
Do not introduce a new abstraction until there is a concrete second use,
replaceable dependency, or independently meaningful responsibility.

## Safety
Do not read credentials or files outside the repository unless requested.
Do not publish, deploy, push, or run destructive commands without approval.

## Project specifics
<only genuinely non-obvious commands, invariants and boundaries>
```

This is intentionally shorter than many current vendor examples. Codex automatically loads hierarchical `AGENTS.md` files; Claude Code supports repository/global instructions and permission configuration; GitHub Copilot supports repository instructions, skills and hooks. But the best 2026 empirical evidence argues that additional persistent prose has real context and exploration costs, so information that can be encoded as a compiler option, lint rule, script or test should normally be encoded there instead. citeturn685221search2turn413289search2turn973383academia7

### Canonical verification pipeline

For every language, expose a fast local command such as:

```bash
./scripts/check
```

It should run, in order:

```text
format/check
→ type or compile check
→ lint
→ fast unit tests
→ relevant integration tests
→ architecture rules if configured
→ lightweight security/dependency checks
```

This ordering surfaces cheap failures early. The script should be the same command used locally, by the coding agent and in CI. When the full suite becomes slow, split it into `check` and `check-full`, but keep `check` strong enough that a successful change is safe to become the next agent's starting point. The reason is directly supported by SWE-Maintain's accumulated-regression findings. citeturn973383academia9

For **TypeScript**, a good baseline is TypeScript `strict`, normally `noUncheckedIndexedAccess`, a mainstream formatter, typed ESLint rules where they pay for themselves, and the project's test runner. TypeScript documents `strict` as enabling its family of stricter checks, while `noUncheckedIndexedAccess` extends checking of indexed properties. `typescript-eslint` offers type-aware strict lint configurations. citeturn696402search0turn696402search43turn696402search47

For **Python**, use Ruff for formatting/linting plus one static type checker—Pyright, basedpyright, mypy or `ty` depending project needs—and pytest or an equivalent test runner. Ruff intentionally combines the functions of multiple older Python lint/format tools, making it attractive where minimising toolchain overhead matters. Do not demand complete typing of exploratory scripts from the first commit; make externally consumed APIs, domain types and stable modules stricter first. Ruff's scope is linting/formatting rather than static type checking, so a separate checker is needed where type guarantees matter. citeturn696402search11turn696402search15

For **Rust**, `cargo fmt --check`, `cargo check` or build, `cargo clippy -- -D warnings` with carefully selected lint exceptions, and `cargo test` provide a strong language-native baseline. `cargo-deny` becomes attractive where dependency advisories, licences, source provenance or banned crates matter. citeturn696402search1turn470779search2

### Behavioural testing strategy

Use three levels rather than attempting exhaustive coverage:

**Focused unit or property tests** should cover deterministic domain logic and meaningful edge cases. **Integration tests** should cover adapters and boundaries where a mistaken assumption about a database, filesystem, network API or parser is plausible. **A small number of end-to-end smoke tests** should prove that the main user-visible path actually works.

When fixing a bug, require a regression test that would have failed before the fix whenever practical. When implementing a feature whose requirement is discovered experimentally, it is acceptable to delay formalising the test until the intended behaviour becomes clear—but before accepting the change as a stable baseline, encode the important behavioural contract. This uses tests as persistent memory rather than as a measure of developer virtue, which is the interpretation best aligned with the agent-maintenance evidence. citeturn973383academia9turn381654search5

Coverage percentage should be diagnostic, not a universal gate. High line coverage can coexist with poor assertions or missing behaviours, and a numeric target is particularly vulnerable to Goodhart-style optimisation by an agent.

### Architecture constraints

Do **not** install an architecture framework simply to say the project has one. Add a machine-enforced rule when violating a boundary would create a real future cost.

For TypeScript/JavaScript, `dependency-cruiser` can forbid imports, detect cycles and validate dependency relationships. For Python, Import Linter supports forbidden-dependency and layered contracts. These are well suited to rules such as "domain code cannot import the HTTP client" or "storage adapters cannot depend on UI code". citeturn470779search3turn470779search9turn470779search0

For Rust, crate boundaries already provide a stronger structural unit than a Python module or TypeScript file. Start with sensible crates/modules and visibility; add specialised dependency policy tooling only if the project develops a concrete need.

An architecture rule should generally be expressible in one sentence and justified by an actual replacement or responsibility boundary. If explaining the rule requires a page of taxonomy, it is probably too elaborate for the baseline.

### Security and execution environment

The minimum security baseline is:

- lock dependencies and review dependency changes;
- run an ecosystem dependency/advisory check;
- keep credentials out of repository files and normal agent context;
- give agents only the filesystem/network/tool permissions they need;
- execute untrusted project commands in a disposable environment where practical;
- add SAST for externally exposed or security-sensitive applications;
- test authentication, authorisation, parsing and input-validation boundaries explicitly.

This layering addresses the key lesson from SUSVIBES: correct-looking functionality is not evidence of secure implementation. citeturn704345search5

CodeQL is a reasonable heavier-weight SAST option because it supports all three target languages; Semgrep provides cross-language rule-based analysis and can run locally and in CI. For low-risk personal utilities, running every advanced security scanner on every edit is unnecessary; dependency auditing plus language-native checks and boundary tests is a more economical starting point, with SAST added when the software accepts untrusted input, exposes a service, processes secrets or has meaningful security consequences. citeturn696402search10turn696402search6

A Dev Container is the most portable mainstream option if container-based development is acceptable because its environment definition lives in the repository and can be used by multiple supporting tools. Pin image/tool versions and retain language lockfiles inside it; a mutable `latest` container plus unlocked dependencies is not meaningfully reproducible. citeturn470779search1turn470779search39

### Agent workflow

For a normal task, use a short loop:

**Explore → state intended change → implement → run targeted checks → run canonical check → inspect diff → independent review when warranted → fix → run canonical check again → commit.**

Do not require a formal design document before every implementation. For a local bug fix the "plan" might be two sentences. For a cross-cutting change, ask the agent first to identify affected modules, preserved behaviour and likely tests; allow implementation to revise that plan when exploration reveals new facts. This accommodates exploratory development without discarding planning entirely.

A high-value reusable **review skill** should ask an independent agent to inspect the finished diff and repository state, looking particularly for:

```text
1. behavioural regressions or missing edge cases;
2. incorrect assumptions about callers or external APIs;
3. input validation and error-handling failures;
4. security boundary mistakes;
5. unnecessary coupling or duplicated concepts;
6. tests that fail to establish the claimed behaviour;
7. simpler changes that preserve the same behaviour.
```

The review should produce specific findings, not an aesthetic score. After review fixes, rerun deterministic verification. Independent review is among the few agent-workflow interventions with a substantial late-2026 controlled evidence base. citeturn973383academia6

For small changes, skip independent review if all of these are true: the diff is narrow, behaviour is well-covered, no security/external-I/O boundary changed, and the canonical checks are strong. This is a cost optimisation, not a research finding.

### Harness choice and portability

The baseline should not depend heavily on one harness because the most valuable assets—tests, scripts, type configuration, architecture checks, git history and short repository instructions—are ordinary repository artefacts.

**Codex** supports hierarchical `AGENTS.md` instructions, skills, sandboxes, sessions and subagent delegation; its API/harness documentation explicitly supports sandbox capabilities and reusable skills. citeturn685221search2turn685221search3turn685221search6

**Claude Code** exposes explicit tool allow/deny controls and permission modes; Anthropic's own guidance for long-running agentic work emphasises keeping verification artefacts and setup scripts in the filesystem so fresh contexts can rediscover state. citeturn685221search0turn685221search1

**GitHub Copilot's agent surfaces** support persistent instructions, reusable skills and hooks. Its hooks are particularly useful because they execute code rather than merely asking the model to follow a rule, and `preToolUse` can approve or deny actions while post-action hooks can run checks or logging. citeturn413289search1turn413289search4

**Aider** remains distinctive for explicit git integration, automatic lint/test feedback and a repository map. Its repository map exposes important classes, functions, signatures and relationships in a compact form; its lint/test integration can automatically return failures to the model. citeturn413289search5turn413289search9

**OpenHands** remains relevant where open-source/self-hostable orchestration and sandbox customisation are priorities; current documentation exposes configurable sandbox container images, MCP integration and task/session APIs. citeturn685221search8

**Cursor** provides repository rules, autonomous/background-agent operation and agent tools, but its value should be separated from any assumption that an IDE-integrated agent is inherently more correct. The METR RCT is a reminder that an attractive interactive workflow does not guarantee net time savings for experienced developers in mature codebases. citeturn413289search24turn704345search7

A sensible portability strategy is therefore to keep harness-specific files thin and derive them from the same repository facts. `AGENTS.md`, `CLAUDE.md`, Copilot instructions and Cursor rules should not each become independent design documents.

## Optional enhancements and when they become worthwhile

**Architecture dependency enforcement** becomes worthwhile once a repository has two or more important subsystems and accidental cross-imports begin appearing. At that point, a ten-line Import Linter or dependency-cruiser rule is preferable to another paragraph telling the agent what not to import. citeturn470779search0turn470779search3

**Independent review on every meaningful change** becomes worthwhile as project lifetime grows, because later agents inherit every accepted patch. The 2026 verification results indicate a favourable accuracy/cost trade-off, and longitudinal maintenance studies make compounding defects a concrete risk rather than a theoretical one. citeturn973383academia6turn973383academia9

**CodeQL or expanded Semgrep rules** become worthwhile for network-facing software, authentication, sensitive data, parsers and projects accepting untrusted input. SUSVIBES provides the strongest reason to move security checking out of prompt text in such projects. citeturn704345search5turn696402search10

**Worktrees or isolated branches per agent** become worthwhile when multiple agent tasks run concurrently. Change isolation lowers the cost of abandoning a bad trajectory and prevents one unfinished change from becoming another agent's context. This is a pragmatic git-based recommendation rather than one established by a controlled agent study.

**Property-based testing, mutation testing and fuzzing** become worthwhile when the domain has rich invariants or parsers and examples are unlikely to cover the input space. They should be targeted rather than compulsory because execution cost and investigation of failures can be high.

**Repository maps, code graphs or dedicated retrieval** become worthwhile when ordinary search begins consuming appreciable agent time or agents repeatedly edit the wrong files. Current retrieval benchmarks show meaningful headroom but no universally superior mechanism, so adoption should be driven by observed retrieval failures rather than by repository size alone. citeturn381654academia10turn381654search1

**Multi-agent ensembles beyond one reviewer** should remain experimental. The independent-review evidence is encouraging, but adding planners, test writers, architecture critics, security critics and synthesiser agents multiplies token cost and creates correlated-review risks. The October 2026 verification study found some additional benefit from more critics or review rounds, but the marginal gains were smaller than the first independent review. citeturn973383academia6

**Long-term agent memory** should likewise remain optional. Persist facts that are expensive to rediscover—external constraints, migration status, known hazards—but prefer repository state, tests and versioned decisions over opaque conversational memory. The negative AGENTS.md results provide a cautionary analogue: more retained context is not automatically better context. citeturn973383academia7

## Evaluation plan and annotated primary sources

A solo developer does not need a new benchmark suite. The most informative evaluation is a **small longitudinal experiment over real work**, because existing public evaluations underrepresent exploratory requirement discovery and because some established benchmarks are contaminated. citeturn704345search1turn661920academia8

Use two small repositories or two substantial features, ideally one TypeScript/Python application and one project in whichever second language you expect to use regularly. Construct a sequence of approximately 8–12 changes per project: initial capability, changed requirement, bug fix, new integration, replacement of one external dependency, error-handling change, moderate refactor and a final feature that touches earlier work. Do not publish the exact task sequence before running the experiment.

Record for every change:

| Outcome | Why it matters |
|---|---|
| Task passes intended behavioural checks | Immediate correctness |
| All prior behavioural checks still pass | Longitudinal correctness |
| Human intervention minutes | Central objective: human effort |
| Agent wall-clock time | Operational cost |
| Approximate tokens / model cost | Economic cost |
| Number of failed verification loops | Diagnostic burden |
| Files/modules changed | Change locality |
| New cross-module dependencies | Coupling/ripple indicator |
| Reviewer findings that produced real fixes | Value of independent review |
| Security defects at trust boundaries | Robustness |
| Success of the *next* modification | Actual maintainability |

This directly borrows the important idea behind CodeThread, SWE-CI and SWE-Maintain: evaluate the software as **history accumulates**, not as a series of resets to pristine human code. citeturn973383academia8turn661920academia8turn973383academia9

The first experiment should test **independent review**, because it has both meaningful evidence and a measurable cost. Randomly enable a fresh reviewer for half the non-trivial changes. Count only findings that lead to a change subsequently supported by a test, reproduction or clearly justified defect. Compare regressions, human intervention and model cost. The existing study predicts an accuracy benefit, but your tasks and model/harness may differ substantially. citeturn973383academia6

The second should test **minimal versus extensive repository instructions**. Keep the baseline file to commands and hard constraints. On alternating comparable tasks, add richer architecture/style/process guidance. Measure success, tokens, exploration actions and human corrections. The prior evidence predicts little correctness benefit and some cost from the larger file, so the purpose is not to reproduce a settled result but to determine whether *your particular repository knowledge* is unusually valuable. citeturn973383academia7turn381654search3

The third should test **machine-enforced architecture versus textual architecture guidance** after a real boundary exists. For example, prohibit domain → adapter or UI → persistence imports using Import Linter or dependency-cruiser in one branch while giving only prose guidance in another sequence. Measure violations and the time spent correcting them. The tool capabilities are established, but the reduction in total agent-development effort is not. citeturn470779search0turn470779search3

The fourth should test **retrieval assistance only if retrieval is observed to be a problem**. Compare native agent exploration against a repository map or structural retrieval on tasks that cross multiple modules. Record time/token use, whether relevant files were found before the first edit and whether unnecessary files were modified. Current benchmarks show enough variation among retrieval methods that a local experiment is genuinely decision-relevant. citeturn381654search1turn381654academia10

Avoid evaluating configurations primarily by code-quality scores from another LLM or by static metrics such as cyclomatic complexity. Use them only as secondary diagnostics. CodeThread supplies direct evidence that common maintainability metrics can fail to explain actual agent-on-agent maintenance performance, and public benchmark contamination further argues for private behavioural evaluation. citeturn973383academia8turn704345search1

The most important sources for continuing this work are:

**Parnas, “On the Criteria to Be Used in Decomposing Systems into Modules” (1972).** The foundational primary source for information hiding and change-oriented decomposition. Its argument is conceptual and illustrated rather than a modern controlled experiment, so it should guide reasoning rather than act as quantitative proof. citeturn636135search0

**Jimenez et al., SWE-bench (ICLR 2024).** Established real-repository issue resolution as a standard agent evaluation paradigm. Its Verified subset later became problematic for frontier-model comparisons because of contamination, which itself is now an important lesson in evaluation design. citeturn704345search0turn704345search1

**Yang et al., SWE-Agent (NeurIPS 2024).** Demonstrated that the agent-computer interface—navigation, editing and execution tools—can materially affect software-engineering performance, establishing the harness as a substantive part of the system rather than a neutral wrapper. citeturn381654search6

**Miserendino et al., SWE-Lancer (ICML 2025).** More than 1,400 real freelance tasks with end-to-end grading, useful evidence that realistic software work remained far from solved even as SWE-bench scores rose. citeturn704345search4

**Becker et al., METR developer-productivity RCT (2025).** Sixteen experienced developers, 246 tasks, early-2025 Cursor/Claude tooling, and a measured 19% slowdown despite strong perceived speed-up. Its model generation is now old, but its randomised field methodology and warning about subjective productivity remain highly relevant. citeturn704345search7

**Badertdinov et al., SWE-rebench (NeurIPS 2025).** Introduces continuous extraction of fresh interactive tasks and provides direct evidence that static benchmark results can be inflated by contamination. citeturn704345search6

**Zhao et al., SUSVIBES (ICML 2026).** One of the most important security results for agentic coding: functional correctness substantially exceeded secure correctness in tested settings, and simple security hints did not solve the problem. citeturn704345search5

**Gloaguen et al., “Evaluating AGENTS.md” (2026).** Controlled evaluation of repository context files; found no success improvement and more than 20% inference-cost increase, supporting small, targeted persistent instruction files rather than comprehensive manuals. citeturn973383academia7

**Li et al., ContextBench (2026).** 1,136 issues, 66 repositories, eight languages and annotated gold context; directly measures the under-studied file/context retrieval stage of coding-agent work. citeturn381654academia10

**Patel et al., CodeThread / “Is Agent Code Less Maintainable Than Human Code?” (EMNLP 2026).** Controlled downstream modification experiment across four agents and four benchmarks; reports up to a 13.1% resolution drop from agent-produced bases and finds traditional maintainability metrics insufficient to explain it. citeturn973383search2

**Pan et al., SWE-Maintain (October 2026).** Perhaps the most practically useful current maintenance result: 1,996 paired later events show that accumulated failing behaviour explains much of the downstream penalty, while agent-written histories that preserve earlier tests do not show a statistically clear intrinsic maintenance disadvantage. citeturn973383academia9

**Zhang et al., “Rethinking Verification in Agent Harnesses” (25 October 2026).** Very recent and therefore not yet backed by long-term replication, but unusually comprehensive across seven frontier coding models and 17 verification designs. Its independent-review result is strong enough to justify a small practical trial now. citeturn973383academia6

The resulting initial configuration is deliberately less ambitious than many "AI-native development" frameworks. Its core is ordinary software-engineering machinery: a small repository with explicit boundaries, tests that accumulate behavioural knowledge, strong language-native checks, a reproducible execution environment, git checkpoints, deterministic security safeguards, minimal persistent instructions and one independent review pass when the risk justifies it. The available evidence supports **making correctness and structure executable wherever possible**, while treating extensive prompting, elaborate upfront design, static maintainability scores and large agent organisations as hypotheses to test rather than prerequisites for high-quality agentic software development.