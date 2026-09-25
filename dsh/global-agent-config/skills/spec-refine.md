---
name: spec-refine
description: Interview the user about a specification in order to get the spec precise enough to be build ready. Use when the user wants to refine an incomplete idea into something ready to build.
disable-model-invocation: true
---

Interview the user about until you reach a shared understanding about a spec - the spec may be given by referencing a file or in chat, or both. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

Before asking the user questions in each round, filter out questions if you can avoid the need to have them answered based on the following rules:

Rule 1) If you could avoid making a choice now by architecting the code in a decoupled, composable or extensible way so that different options can be easily changed later, treat doing that as the answer to the question rather than asking.

Rule 2) Is it necessary to build the thing you would ask about in order to create a "minimum viable product" like implementation of the spec. If not, treat the answer as not to build it yet rather than asking.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.

When the session is finished, write out a new refined spec under `.agent-diaries/refined-specs/${date in YYYY-MM-DD}-${feature name}-${revision_number}.md`. The refined should include enough detail for another agent to be able to build.

The revision number will be `001` unless that file already exists - if so choose the lowest number that does not have an existing file.