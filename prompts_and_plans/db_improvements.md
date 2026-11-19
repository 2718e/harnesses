Want to make 2 improvements to shared dev db - or to how it's used in this project

1. instead of mounting a local checkout, use the github repo (at https://github.com/2718e/shared-dev-db) to initially set it up.

2. set up incremental backups using pgBackRest, this will be to a mounted host folder with write permissions. Backups are for all databases in the container - don't want to have to set up backups again for each new project.