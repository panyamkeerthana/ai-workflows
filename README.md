# AI workflows, driven by Goose AI

For Goose AI to be able to access Jira tickets you need an MCP Server.
In this workflows we are using [MCP server for Atlassian tools](https://github.com/sooperset/mcp-atlassian).

## Configure

1. Copy `env.template` to `.env` and update it as follows
2. Set your Gemini key in `GOOGLE_API_KEY` (take it from Google Cloud -> API & Services -> Credentials -> API Keys -> show key)
3. Set your Jira Personal Token in `JIRA_PERSONAL_TOKEN` (create PATs in your Jira/Confluence profile settings - usually under "Personal Access Tokens")
4. Change (if needed) the `JIRA_URL` now pointing at `https://issues.redhat.com/`
5. Set your Gitlab Personal Token `GITLAB_TOKEN` with read permissions (read_user, read_repository, read_api).  Note that some recipes require write access to Gitlab: use it at your own risk.

If you need to change the llm provider and model, they are stored in the Goose config file: `goose-container/goose-config.yaml` (`GOOSE_PROVIDER`, `GOOSE_MODEL`)

## Build

`make build`

## Run Goose - interactively - with the MCP Atlassian server

Run the Jira MCP server from Atlassian and Goose separately, otherwise not all the input from your terminal 
is always redirected to the Goose container.

1. `make run-mcp-atlassian`
2. `make run-goose`
3. Type *List all In Progress issues at https://issues.redhat.com/projects/LD* and wait for the output.
4. `make clean`

You can further manually run test and run the Goose recipes which are mounted into the container at `/home/goose/recipes`.

## Run local Goose recipes

The recipes are defined in `goose-recipes/`.  If you want to run `goose-recipes/<recipe>.yaml`, run the following:

1. `make <recipe>`
2. `make clean`

## Development

This project uses [pre-commit](https://pre-commit.com/) hooks. To set up:

```bash
pip install pre-commit
pre-commit install
```
