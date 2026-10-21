IMAGE := agentic_local_mcp_customer_record
AGENT_CONTAINER := customer_record_agent
MCP_CONTAINER := customer_record_mcp
NETWORK := customer_record_lab
EXPLOIT_DIR := ../../exploitation/agentic_bulk_delete
PODMAN ?= podman
HOST_PORT ?= 8011

.PHONY: help install sync lock build up down stop test test-unit attack replay all format mypy ollama-pull ollama-ready

help:
	@echo "Agentic Local MCP Customer Record - Available Commands:"
	@echo "  make build      - Build the sandbox image"
	@echo "  make up         - Start the vulnerable baseline locally"
	@echo "  make test       - Verify agent and MCP health"
	@echo "  make test-unit  - Run unit and regression tests"
	@echo "  make attack     - Run the payload/defense matrix"
	@echo "  make replay     - Run the offline deterministic replay"
	@echo "  make stop       - Remove lab containers and network"
	@echo "  make all        - Test, build, attack, and stop"

install:
	pip install uv

sync:
	uv sync --frozen

lock:
	uv lock

ollama-pull:
	ollama pull gpt-oss:20b

ollama-ready:
	@curl -sf http://localhost:11434/api/version >/dev/null || (echo "Ollama is not ready on :11434"; exit 1)

build:
	$(PODMAN) build -f Containerfile -t $(IMAGE) .
	-$(PODMAN) network create --driver bridge $(NETWORK) 2>/dev/null || true

up: ollama-ready
	-$(PODMAN) rm -f $(AGENT_CONTAINER) $(MCP_CONTAINER) 2>/dev/null || true
	-$(PODMAN) network create --driver bridge $(NETWORK) 2>/dev/null || true
	$(PODMAN) run -d --name $(MCP_CONTAINER) --network $(NETWORK) \
		-e TOOL_OUTPUT=escaped \
		--entrypoint uv $(IMAGE) run python mcp/customer_records.py
	$(PODMAN) run -d --name $(AGENT_CONTAINER) --network $(NETWORK) -p $(HOST_PORT):8000 \
		-e MCP_SERVER_URL=http://$(MCP_CONTAINER):8000/sse \
		$(IMAGE)

test:
	@for i in $$(seq 1 30); do curl -sf http://localhost:$(HOST_PORT)/health >/dev/null && break; sleep 1; done
	@curl -sf http://localhost:$(HOST_PORT)/health | grep ok
	@for i in $$(seq 1 30); do \
		$(PODMAN) exec $(AGENT_CONTAINER) python -c "import socket; socket.create_connection(('$(MCP_CONTAINER)', 8000), 2)" >/dev/null 2>&1 && break; \
		sleep 1; \
	done
	@$(PODMAN) exec $(AGENT_CONTAINER) python -c "import socket; socket.create_connection(('$(MCP_CONTAINER)', 8000), 2)"

test-unit: sync
	PYTHONPATH=.:../../exploitation/agentic_bulk_delete uv run pytest \
		tests/ ../../exploitation/agentic_bulk_delete/tests/

attack: build up test
	$(MAKE) -C $(EXPLOIT_DIR) attack

replay:
	$(MAKE) -C $(EXPLOIT_DIR) replay

stop down:
	-$(PODMAN) rm -f $(AGENT_CONTAINER) $(MCP_CONTAINER) 2>/dev/null || true
	-$(PODMAN) network rm $(NETWORK) 2>/dev/null || true

all: test-unit build up test
	$(MAKE) -C $(EXPLOIT_DIR) attack
	$(MAKE) stop

format:
	uv run isort --profile black app/ mcp/ tests/
	uv run black app/ mcp/ tests/

mypy:
	uv run mypy app/ mcp/
