## THe problem

I seem to have Forgotten how I set up the shared database in the VM (defined in harnesses/4microvm).

## What to do

Okay.So I think like setting up the VM and also setting up the shared dev database should be like an easy one just command thing and I guess since the database might already exist that setup should be like idempotent.

I don't want to have a bunch of manual steps in the readme.that people would have to do to set up.This might have been good while we were trying to debug, but...I guess idea is - suppose we had a fresh checkout. then want to get to a point where, like, the initial setup is basically brainless.

Also...I kind of want the database to be like really easy to use once it is created. So...Maybe we should set something.in the VM likepossibly an environment variable that says like where the database is or like a base database URL that doesn't tell you specifically which database you'd be connecting to because that would be different for each project.

We can modify the shared devdb project as well if that makes things easier. But...Keep in mind that the shared DevDB project itself should be agnostic as to whether or not it's running in a VM or on a host or like wherever.

Summary: make setting up the VM with a shared dev database ready to go easy, simple and clean.

## Note

### Future changes context

Some higher level thoughts - out of scope for making these changes, but mentioning just in case it affects design:

We should probably move to thinking of running the projects inside the vm as like the main scenario (e.g. *other than* harnesses/4microvm itself the default .env file can be for the VM environment. Possibly also the idea of separate agent venvs to avoid host conflict can be revisited.

Also, I'm starting to realise that managing A shared dev database may not actually be easier than being a database container in each project, but the reason for doing that is more as a helper for allowing the database connections to be abstracted from the project logic as opposed to just a convenience feature.

### Current status (as of 2026-10-31 ant 10:36 AM)

I just ran `just stop` and `just delete` I'm not sure of the status of the current database disk, but at the current time I haven't used shared-dev-db either in the vm or on the host, so we don't have to worry about deleting and recreating if it helps keep things clean.