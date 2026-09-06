# High level goal

Set up for use of Pi harness

## Things that should already be in place

Have initialised this project by copying a setup for deepseek harness and removed some things specific to that harness. 

- dockerfile and compose file to only mount and give agent access to specific folders
- .gitignored .env file for API Keys 

The dockerfile will be incomplete because I deleted lines that seemed specific to deepseek harness.

## Want to set up

Ability to add *read only* volumes. As an example, the folder /media/dan/data/dev/datasets/test can be mounted as read only. Intended use case would be that for projects that involve analysing data, I want to be able to have the code and potentially agent read the data but not be able to modify it.

Setup for Pi harness as a node project (i.e. so we can install dependencies and plugins by specifying in a package.json)

If something can be setup so it can be installed as part of `npm install` or equivalent don't directly install it via dockerfile (though we can run `npm install` or equivalent itself during the `docker build`)

## Initial capabilities to setup

I think Following capabilities seem to need to be provided as plugins / modules for pi harness:

- web search

Research some options and select a sensible default, ask me to approve.
