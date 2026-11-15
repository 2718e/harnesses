# Various improvements

remove dsh subproject, consider 4microvm to be the defacto only project, somehow document this e.g. in agents.md. maybe fix up badly worded or unnecessary agents.md

add just to the VM so that agents can use and validate justfiles

If possible, add lima iteself to the VM so if agent works on a separate checkout of this project inside the vm it can test and validate (i think nested virtualisation is theoretically possible at least, but what would happen if it tries to create a disk that's the same size as the first level VM, any other gotchas - note, nested vm is only intended for allowing agents in the vm to work on this project and validate, not for actual use)

set up so that the tailscale ID of the VM survives recreation (choice: persist data in the separate disk for the db or via a host mount or some other mechanism?)

If possible - add t3 code to the vm, allow it to use the codex install in the vm, and allow me to reach it from tailscale (don't remove the mechanisms for ssh and tmux based remote access - I'm still trying out multiple mechanisms so want to be able to use either or.)