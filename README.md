# AI workflows, driven by Goose AI

For Goose AI to be able to access Jira tickets you need an MCP Server.
In this workflows we are using [MCP server for Atlassian tools](https://github.com/sooperset/mcp-atlassian).

## Configure

1. Copy `.env.template` in `.env` and open the newly created `.env` file.
2. Set your Gemini key in `GOOGLE_API_KEY` (take it from Google Cloud -> API & Services -> Credentials -> API Keys -> show key)
3. Set your Jira Personal Token in `JIRA_PERSONAL_TOKEN` (create PATs in your Jira/Confluence profile settings - usually under "Personal Access Tokens")
4. Change (if needed) the `JIRA_URL` now pointing at `https://issues.redhat.com/`
5. Set your Gitlab Personal Token `GITLAB_TOKEN` with read permissions (read_user, read_repository, read_api).

If you need to change the llm provider and model, they are stored in the goose config file: `goose-container/goose-config.yaml` (`GOOSE_PROVIDER`, `GOOSE_MODEL`)

If you want to use Goose AI with remote recipes, set the repo from where to take the recipes in `goose-container/goose-config.yaml` -> `GOOSE_RECIPE_GITHUB_REPO` with `username/repo`.
*Warning: while developing it is difficult to use a remote recipe (since it has not yet been deployed in main or merged in target repo, I have found no way to dinamically set a branch or fork for playing with the recipe).*

## Build

`make build`

## Run goose - interactively - with the mcp atlassian server

Run mcp server and goose separately, otherwise not all the input from your terminal 
is always redirected to the goose container.

1. `make run-mcp-server`
2. `make run-goose`
3. Type *List all In Progress issues at https://issues.redhat.com/projects/LD* and wait for the output.
4. `make clean`

## Run local goose recipes

The recipes are defined in `goose-recipes/`.

1. `make <recipe-name-without-yaml-extension>`
2. `make clean`
