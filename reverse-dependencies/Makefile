PACKAGE ?= podman
.PHONY: reverse-dependencies
reverse-dependencies:
	goose recipe validate ./reverse-dependencies.yaml
	GOOSE_MODE="auto" goose run --recipe ./reverse-dependencies.yaml --params package=$(PACKAGE)
