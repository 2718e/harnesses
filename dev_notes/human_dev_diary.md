Agent used a mount from a gitignored file to set up the database - which is fine during setup, but creates a dependency on a gitignored file (where the mount defined)

...

Now find myself thinking but wait with bind mounted project folders how do we configure the separate DB, or more generally do we now need to have different environment or .env files for the VM and host.

Possibly this is a problem with trying to go through some state that's inbetween agent assisted development and full software factory. End state should probably have all projects as completely separate checkouts or worktree or something, maybe tolerate the issue for now.

COme to think of it I could probably just connect the manual dev tools to the vm as well maybe should move away from the idea of developing on host directly at all.

