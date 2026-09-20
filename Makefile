.PHONY: all help docs-serve serve docs-build build docs-clean clean

all: docs-clean docs-build docs-serve

help:
	@echo "GenAI Red Team Lab - Make targets:"
	@echo "  make all                        - Clean previous build artifacts and spin up the website locally"
	@echo "  make docs-serve (or make serve) - Spin up the website locally with live reload"
	@echo "  make docs-build (or make build) - Build the website into ./site"
	@echo "  make docs-clean (or make clean) - Remove the ./site directory"

docs-serve:
	uvx --with mkdocs-material mkdocs serve

serve: docs-serve

docs-build:
	uvx --with mkdocs-material mkdocs build

build: docs-build

docs-clean:
	rm -rf site/

clean: docs-clean
