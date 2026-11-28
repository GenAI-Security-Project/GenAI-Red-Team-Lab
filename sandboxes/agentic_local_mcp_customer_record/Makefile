IMAGE := agentic_local_mcp_customer_record
AGENT_CONTAINER := customer_record_agent
MCP_CONTAINER := customer_record_mcp
NETWORK := customer_record_lab
EXPLOIT_DIR := ../../exploitation/agentic_bulk_delete
PODMAN ?= podman
HOST_PORT ?= 8011
MODEL ?= gpt-oss:20b
MODEL_BASE_URL ?= http://host.containers.internal:11434/v1
MODEL_READY_URL ?= http://localhost:11434/api/version
RESULTS_SUBDIR ?=

.PHONY: help install sync lock build up down stop test test-unit test-container attack replay all format mypy ollama-pull ollama-ready model-ready

help:
	@echo "Agentic Local MCP Customer Record - Available Commands:"
	@echo "  make build      - Build the sandbox image"
	@echo "  make up         - Start the vulnerable baseline locally"
	@echo "  make test       - Verify agent and MCP health"
	@echo "  make test-unit  - Run unit and regression tests"
	@echo "  make test-container - Run deterministic real-container checks"
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

model-ready:
	@curl -sf "$(MODEL_READY_URL)" >/dev/null || (echo "Model backend is not ready at $(MODEL_READY_URL)"; exit 1)

ollama-ready: model-ready

build:
	$(PODMAN) build -f Containerfile -t $(IMAGE) .
	-$(PODMAN) network create --driver bridge $(NETWORK) 2>/dev/null || true

up: model-ready
	-$(PODMAN) rm -f $(AGENT_CONTAINER) $(MCP_CONTAINER) 2>/dev/null || true
	-$(PODMAN) network create --driver bridge $(NETWORK) 2>/dev/null || true
	$(PODMAN) run -d --name $(MCP_CONTAINER) --network $(NETWORK) \
		-e TOOL_OUTPUT=escaped \
		--entrypoint uv $(IMAGE) run python mcp/customer_records.py
	$(PODMAN) run -d --name $(AGENT_CONTAINER) --network $(NETWORK) -p 127.0.0.1:$(HOST_PORT):8000 \
		-e MCP_SERVER_URL=http://$(MCP_CONTAINER):8000/sse \
		-e OLLAMA_BASE_URL=$(MODEL_BASE_URL) \
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
	uv run pytest tests/
	$(MAKE) -C $(EXPLOIT_DIR) test

test-container: build
	PODMAN="$(PODMAN)" $(MAKE) -C $(EXPLOIT_DIR) test-container

attack: build up test
	TARGET_MODEL="$(MODEL)" RESULTS_SUBDIR="$(RESULTS_SUBDIR)" \
		$(MAKE) -C $(EXPLOIT_DIR) attack

replay:
	$(MAKE) -C $(EXPLOIT_DIR) replay

stop down:
	-$(PODMAN) rm -f $(AGENT_CONTAINER) $(MCP_CONTAINER) 2>/dev/null || true
	-$(PODMAN) network rm $(NETWORK) 2>/dev/null || true

all: test-unit build up test
	TARGET_MODEL="$(MODEL)" RESULTS_SUBDIR="$(RESULTS_SUBDIR)" \
		$(MAKE) -C $(EXPLOIT_DIR) attack
	$(MAKE) stop

format:
	uv run isort --profile black app/ mcp/ tests/
	uv run black app/ mcp/ tests/

mypy:
	uv run mypy app/ mcp/
