## Background context

So we've previously been trying to set up agent harnesses inside a VM (4microvm subfolder). it isn't entirely working and some of the things we are trying to do are on reflection the wrong solution to a problem we don't have yet.

In particular The actual problem we were trying to solve by Trying to have a web interface to the harnesses rather than a shell one is remote access, which that's a later and different problem. Don't need to solve it now. 

This also means trying to route from DSH to Codex or something else is then also not really necessary (were in turn only doing that because DSH has a web interface whereas codex is CLI.)

DO want to keep giving the agents tools like ast-grep and tree sitter.

DO still want to have multiple harnesses available.

## Modifications and fixes

We probably don't need to run DSH as a system service. We can just go inside the shell for now and start the harnesses that way. (similarly for codex, though in that case I think that's already the default)

INstalling of "koffi" seemed to Give an error based on the tmp/doctorlogs.txt logs.There's also a warning that we shouldn't be referencing the LIMA_CIDATA variables in provisioning scripts. Why do we need "koffi" - if we do lets fix the error, and also stop referencing LIMA_CIDATA variables in provisioning scripts.