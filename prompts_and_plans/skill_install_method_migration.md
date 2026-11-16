Want to change how this project installs skills

## Desired state (first mvp)

Skills defined in a separate repo, I've created a `skills` folder locally adjacent to the folder for this repo that will be used.

The skills repo mounted into the vm.

Skill installation will use https://github.com/owainlewis/skills referencing the mounted skill repo

Only the project setup skill will be installed at agent level during creation, not the build and review skills. Will in future use the declarative skill installer to install skills mostly in projects, but maybe also at user level (though only at some sort of recreate or sync step, installing user level skills from inside the running vm intenionally not supported)

## Next steps (for context)

Will make the skills repo a public repo and download from there rather than mounting in the vm (so, while in general I want to avoid vm setup depending on project mounts, doing it this way temporarily because want to test that the skill installer is capable of using local repo clones as a reference)

