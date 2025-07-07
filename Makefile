## Public make targets
.PHONY: # Help output
.PHONY: help
.PHONY:
.PHONY: # Manage container image
.PHONY: clean build config
.PHONY:
.PHONY: # Manage MCP server for JIRA
.PHONY: stop-mcp-atlassian run-mcp-atlassian logs-mcp-atlassian
.PHONY:
.PHONY: # Start Goose container without a specific recipe
.PHONY: run-goose run-goose-bash
.PHONY:
.PHONY: # Run Goose with specific recipes
.PHONY: check-jira-tickets
.PHONY: issue-details
.PHONY: rebase-package
.PHONY: reverse-dependencies
.PHONY: triage-issue

## Defaults
COMPOSE ?= podman compose

check-jira-tickets: PROJECT ?= RHEL
check-jira-tickets: COMPONENT ?= cockpit

issue-details: ISSUE ?= RHEL-78418

rebase-package: PACKAGE ?= cockpit
rebase-package: VERSION ?= 339
rebase-package: JIRA_ISSUES ?= "RHEL-123"

reverse-dependencies: PACKAGE ?= podman

triage-issue: ISSUE ?= RHEL-78418

## Operations
build:
	$(COMPOSE) build

run-mcp-atlassian:
	$(COMPOSE) up -d mcp-atlassian

stop-mcp-atlassian:
	$(COMPOSE) down mcp-atlassian

logs-mcp-atlassian:
	$(COMPOSE) logs -f mcp-atlassian

run-goose:
	- $(COMPOSE) up -d goose
	$(COMPOSE) exec goose goose

run-goose-bash:
	- $(COMPOSE) up -d goose
	$(COMPOSE) exec goose bash

check-jira-tickets:
	$(COMPOSE) run --rm \
		--entrypoint /bin/sh goose \
		-c "/usr/local/bin/goose run --recipe recipes/check-jira-tickets.yaml \
			--params project=$(PROJECT) \
			--params component=$(COMPONENT)"

issue-details:
	$(COMPOSE) run --rm \
		--entrypoint /bin/sh goose \
		-c "/usr/local/bin/goose run --recipe recipes/issue-details.yaml \
			--params issue=$(ISSUE)"

triage-issue:
	$(COMPOSE) run --rm \
		--entrypoint /bin/sh goose \
		-c "/home/goose/wait_mcp_server.sh && /usr/local/bin/goose run --recipe recipes/triage-issue.yaml \
			--params issue=$(ISSUE)"

rebase-package:
	$(COMPOSE) run --rm \
		--entrypoint /bin/sh goose \
		-c "set -e; \
			set +x; \
			askpass=\"\$$(mktemp)\"; \
			echo '#!/bin/sh' > \"\$$askpass\"; \
			echo 'echo \$$GITLAB_TOKEN' >> \"\$$askpass\"; \
			chmod +x \"\$$askpass\"; \
			export GIT_ASKPASS=\"\$$askpass\"; \
			/usr/local/bin/goose run --recipe recipes/rebase-package.yaml \
			--params package=$(PACKAGE) \
			--params version=$(VERSION) \
			--params jira_issues=$(JIRA_ISSUES) \
			--params gitlab_user=$(GITLAB_USER) && echo 'Recipe completed. Dropping into shell...' && /bin/bash"

reverse-dependencies:
	$(COMPOSE) run --rm \
		--entrypoint /bin/sh goose \
		-c "/usr/local/bin/goose run --recipe recipes/reverse-dependencies.yaml \
			--params package=$(PACKAGE)"

config: GLOBAL_TEMPLATE = templates/compose.env
config: SECRET_TEMPLATES = $(filter-out $(GLOBAL_TEMPLATE), $(wildcard templates/*))
config:
	mkdir -p .secrets
	cp -n $(SECRET_TEMPLATES) .secrets/
	cp -n $(GLOBAL_TEMPLATE) .env

clean:
	$(COMPOSE) down
	podman volume prune -f

help:
	@echo "Available targets:"
	@echo "  config                      - Copy config templates to .secrets/ and .env"
	@echo "  build                       - Build all images"
	@echo "  run-mcp-atlassian           - Start MCP server in background"
	@echo "  stop-mcp-atlassian          - Stop MCP server"
	@echo "  logs-mcp-atlassian          - Show MCP server logs"
	@echo "  run-goose                   - Run goose interactively"
	@echo "  run-goose-bash              - Run goose with bash shell"
	@echo "  <recipe>                    - To run the recipes/<recipe>.yaml"
	@echo "  clean                       - Stop all services and clean volumes"
