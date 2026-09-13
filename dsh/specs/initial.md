# Description

I want to try out using the deepseek harness

Their official docs say it should be run in a container as a security mitigation

this project is to set up the container.

## More specific concerns.

From experience with other agents, it's a fairly common thing for the agent to autonomously run tests and linters. 
Would this mean the container needs to have this capability? Is it sufficient to just have the language runtimes (likely either node or python)?

Presumably would want to be able to give the container
- read and write access to the project folders
- potentially read only access to other folders on the computer, selectively.

Want the agent to have web search capability so can research non-code related questions related to what projects should actually do as well as write code.

