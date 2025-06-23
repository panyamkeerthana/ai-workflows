.PHONY: build run-mcp-server run-goose run-goose-workflow stop-mcp-server logs-mcp-server clean

PROJECT ?= RHEL
COMPONENT ?= cockpit
COMPOSE ?= podman compose

build:
	$(COMPOSE) build

# MCP server management
run-mcp-server:
	$(COMPOSE) up -d mcp-atlassian

stop-mcp-server:
	$(COMPOSE) down mcp-atlassian

logs-mcp-server:
	$(COMPOSE) logs -f mcp-atlassian

# Goose commands
run-goose:
	$(COMPOSE) run --rm goose

run-goose-bash:
	$(COMPOSE) run --rm --entrypoint /usr/bin/bash goose

# run remote workflow taken from goose-config.yaml -> GOOSE_RECIPE_GITHUB_REPO
run-goose-workflow:
	$(COMPOSE) run --rm \
		--entrypoint /bin/sh goose \
		-c "/usr/local/bin/goose run --recipe check-jira-tickets --params project=$(PROJECT) --params component=$(COMPONENT)"

# run local workflow taken from /home/goose/recipes
run-goose-local-workflow:
	$(COMPOSE) run --rm \
		--entrypoint /bin/sh goose \
		-c "/usr/local/bin/goose run --recipe recipes/check-jira-tickets/recipe.yaml"

clean:
	$(COMPOSE) down
	podman volume prune -f

help:
	@echo "Available targets:"
	@echo "  build                    - Build all images"
	@echo "  run-mcp-server           - Start MCP server in background"
	@echo "  stop-mcp-server          - Stop MCP server"
	@echo "  logs-mcp-server          - Show MCP server logs"
	@echo "  run-goose                - Run goose interactively"
	@echo "  run-goose-bash           - Run goose with bash shell"
	@echo "  run-goose-workflow       - Run goose remote workflow (PROJECT=name, COMPONENT=name)"
	@echo "  run-goose-local-workflow - Run goose local workflow (PROJECT=name, COMPONENT=name)"
	@echo "  clean                     - Stop all services and clean volumes"
