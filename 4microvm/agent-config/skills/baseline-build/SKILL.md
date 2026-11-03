---
name: baseline-build
description: Implement a requested change with verification and a bounded independent review/fix cycle.
---

# Build with review

Optional input: `max_review_passes` (positive integer, default 3).

You are the builder and manage the cycle:

1. Implement the requested change and run the project's verification command.
2. Invoke a fresh reviewer using `baseline-review`. Supply the task requirements
   and change scope, without inheriting your conversation or implementation
   reasoning. The reviewer inspects the shared repository without editing it;
   pause implementation during review.
3. Evaluate findings, fix justified issues, and rerun verification. Explain any
   rejected findings. Repeat review after edits while passes remain.

Count every reviewer invocation against the limit, including failed attempts.
Stop when verification passes and review leaves no unresolved findings, when
blocked, or at the limit. If fresh delegation is unavailable, report that blocker
rather than substituting self-review.

Report verification results, passes used, unresolved findings, and any final
edits that have not been re-reviewed. Reaching the limit is not success.
