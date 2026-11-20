## Idea

Want to be able to install lima itself in the VM, then be able to have the agent in the vm build (and test + validate) on a separate checkout of this project.

## fixing possible gotchas


make sure inner LIMA_HOME is distinct from host (Don’t mount the host’s Lima state, I don't think we were anyway.)

- maybe increase the disk size (100 Gib, which I think is the default)

we need a place to have outer-vm-only projects (not mounted from host to avoid filesystem nesting) - do we already or do we need to set something up?

Can the `just stop` command be modified to raise an error if a nested VM is running?