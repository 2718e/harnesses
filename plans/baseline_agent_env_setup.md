# Rough plan

## High level

Did a deep research run on how to get good quality code from agents, copied it to `plans/plan_references/agentic-coding-deep-research-report.md`

Want to turn this into something usable for projects (presuming for now that the vm defined `4microvm` will be run and then the harnesses installed in it will be used.)

## Notes and ideas so far

separate review sub agent seems one of the most agent specific established good idea. Could define one that will be usable in any project this harness is used in (e.g. something like a `review` skill (though maybe should choose a diffrent name to avoid collisions with those built in to harnesses.) and potentially an instruction at project level to run the review skill after any change)

Seems Codex and most other harnesses use hierarchical approach, no clear way to opt out of things defined at harness level or user level at project level.
Also some tools (linters, type checkers) are specific to implementation languages, or require setup in project.

So maybe most things shouldn't be part of the harness, but maybe could have something like a script or skill for setting up an individual project with the reccomendations, tools, etc. (i.e. won't automatically setup a baseline AGENTS.md that's installed at harness level or user level in the VM, but will have a starter or template that can be setup (merged with existing? skill should probably ask in this case) alongside other tools in 1 command or skill call)

Can be somewhat opinionated to my own tastes (e.g. for this reason we can make using type checking part of the standard setup even for python)

"Descriptive, semantically meaningful names" is mentioned as an adopt now but how to enforce or encourage / steer toward this this. Maybe part of review agent? What does it apply to? (just functions, functions and classes, package or folder, file names as well?) could this conflict with wanting to follow **naming conventions** (or from real-world experience it can conflict with not introducing breaking changes, though maybe not relevant to my own use case.) Maybe could include flagging scenarios where a name is misleading compared to actual use (or is that too vague, ill-defined to be useful)

### Scope note

To my own understanding the research was based on what agentic and general development techniques have evidence for them - with the goal of setting a baseline or sensible default. Should keep the scope based on this, but not preclude adding more specific or complex flows later.

### Proposal for what to create

For a specific structure of what we want to create:

a review skill
Some sort of project setup helper

And make those avaliable to the harnesses on vm creation.