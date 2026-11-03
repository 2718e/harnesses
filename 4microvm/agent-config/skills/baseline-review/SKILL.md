---
name: baseline-review
description: Review a code change when requested by a human or delegated by an agent.
---

# Scope

Optional inputs: change scope and intended behaviour.

Use the requested scope when supplied. Otherwise review staged and unstaged changes. If there are none, review the current branch's changes since its merge base with the base branch. Ask if the base branch is ambiguous.

Use supplied intended behaviour when available. Also infer expectations
from documentation, tests, callers, and surrounding code, distinguishing material
assumptions from explicit requirements. Missing intent does not block review of
internal consistency and other defects.

# Review

inspect the changes, surrounding context, and repository state, looking particularly for:

1. behavioural regressions or missing edge cases;
2. incorrect assumptions about callers or external APIs;
3. input validation and error-handling failures;
4. security boundary mistakes;
5. unnecessary coupling or duplicated concepts;
6. tests that fail to establish the claimed behaviour;
7. simpler changes that preserve the same behaviour.

Also assess whether:

8. names communicate purpose and behaviour clearly in context, including relevant units or side effects;
9. terminology consistently identifies the same concepts and distinguishes different ones, following project conventions.
