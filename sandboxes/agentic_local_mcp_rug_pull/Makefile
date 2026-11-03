IMAGE := agentic_local_mcp_rug_pull
GATEWAY_CONTAINER := rug_pull_gateway
TOOLBOX_CONTAINER := rug_pull_toolbox
WORKSPACE_CONTAINER := rug_pull_workspace
NETWORK := rug_pull_lab
EXPLOIT_DIR := ../../exploitation/mcp_rug_pull
PODMAN ?= podman
HOST_PORT ?= 8012
MODEL_BACKEND ?= ollama
OLLAMA_BASE_URL ?= http://host.containers.internal:11434/v1
# Host-side check only; `make test` checks Ollama again from inside the gateway.
OLLAMA_CHECK_URL ?= http://localhost:11434/api/version

.PHONY: help install sync lock build up down stop test test-unit attack replay all format mypy ollama-pull ollama-ready

help:
	@echo "Agentic Local MCP Rug Pull - Available Commands:"
	@echo "  make build      - Build the sandbox image"
	@echo "  make up         - Start gateway (stage 0), attacker toolbox and workspace"
	@echo "  make test       - Verify gateway health and MCP reachability"
	@echo "  make test-unit  - Run unit, integration and replay tests"
	@echo "  make attack     - Run the profile matrix (restarts gateway and toolbox per profile)"
	@echo "  make replay     - Offline deterministic replay (no model, no containers)"
	@echo "  make stop       - Remove lab containers and network"
	@echo "  make all        - Test, build, attack, and stop"
	@echo ""
	@echo "  MODEL_BACKEND=scripted make attack     - full container plumbing without a GPU"

install:
	pip install uv

sync:
	uv sync --frozen

lock:
	uv lock

ollama-pull:
	ollama pull gpt-oss:20b

ollama-ready:
	@if [ "$(MODEL_BACKEND)" = "ollama" ]; then \
		curl -sf $(OLLAMA_CHECK_URL) >/dev/null || (echo "Ollama is not ready at $(OLLAMA_CHECK_URL)"; exit 1); \
	fi

build:
	$(PODMAN) build -f Containerfile -t $(IMAGE) .
	-$(PODMAN) network create --driver bridge $(NETWORK) 2>/dev/null || true

# podman forwards host proxy vars, so local and lab hosts must bypass the proxy.
up: ollama-ready
	-$(PODMAN) rm -f $(GATEWAY_CONTAINER) $(TOOLBOX_CONTAINER) $(WORKSPACE_CONTAINER) 2>/dev/null || true
	-$(PODMAN) network create --driver bridge $(NETWORK) 2>/dev/null || true
	$(PODMAN) run -d --name $(WORKSPACE_CONTAINER) --network $(NETWORK) \
		--entrypoint uv $(IMAGE) run --no-sync python servers/serve.py workspace
	$(PODMAN) run -d --name $(TOOLBOX_CONTAINER) --network $(NETWORK) \
		--entrypoint uv $(IMAGE) run --no-sync python servers/serve.py toolbox
	$(PODMAN) run -d --name $(GATEWAY_CONTAINER) --network $(NETWORK) \
		-p 127.0.0.1:$(HOST_PORT):8000 \
		-e MODEL_BACKEND=$(MODEL_BACKEND) \
		-e OLLAMA_BASE_URL=$(OLLAMA_BASE_URL) \
		-e NO_PROXY="localhost,127.0.0.1,host.containers.internal,$(TOOLBOX_CONTAINER),$(WORKSPACE_CONTAINER)" \
		-e no_proxy="localhost,127.0.0.1,host.containers.internal,$(TOOLBOX_CONTAINER),$(WORKSPACE_CONTAINER)" \
		-e WORKSPACE_MCP_URL=http://$(WORKSPACE_CONTAINER):8000/sse \
		-e TOOLBOX_MCP_URL=http://$(TOOLBOX_CONTAINER):8000/sse \
		$(IMAGE)

test:
	@for i in $$(seq 1 30); do curl -sf http://localhost:$(HOST_PORT)/health >/dev/null && break; sleep 1; done
	@curl -sf http://localhost:$(HOST_PORT)/health | grep ok
	@for c in $(TOOLBOX_CONTAINER) $(WORKSPACE_CONTAINER); do \
		for i in $$(seq 1 30); do \
			$(PODMAN) exec $(GATEWAY_CONTAINER) python -c "import socket; socket.create_connection(('$$c', 8000), 2)" >/dev/null 2>&1 && break; \
			sleep 1; \
		done; \
		$(PODMAN) exec $(GATEWAY_CONTAINER) python -c "import socket; socket.create_connection(('$$c', 8000), 2)"; \
	done
	@if [ "$(MODEL_BACKEND)" = "ollama" ]; then \
		$(PODMAN) exec $(GATEWAY_CONTAINER) python -c "import urllib.request as u; u.build_opener(u.ProxyHandler({})).open('$(OLLAMA_BASE_URL)/models', timeout=5).read()" \
		|| (echo "The gateway container cannot reach Ollama at $(OLLAMA_BASE_URL): see README"; exit 1); \
	fi

test-unit: sync
	uv run pytest tests/
	@if [ -d $(EXPLOIT_DIR) ]; then $(MAKE) -C $(EXPLOIT_DIR) test; fi

attack: build up test
	MODEL_BACKEND=$(MODEL_BACKEND) $(MAKE) -C $(EXPLOIT_DIR) attack

replay:
	$(MAKE) -C $(EXPLOIT_DIR) replay

stop down:
	-$(PODMAN) rm -f $(GATEWAY_CONTAINER) $(TOOLBOX_CONTAINER) $(WORKSPACE_CONTAINER) 2>/dev/null || true
	-$(PODMAN) network rm $(NETWORK) 2>/dev/null || true

all: test-unit
	status=0; \
	{ $(MAKE) build up test && MODEL_BACKEND=$(MODEL_BACKEND) $(MAKE) -C $(EXPLOIT_DIR) attack; } || status=$$?; \
	$(MAKE) stop; exit $$status

format:
	uv run isort --profile black app/ servers/ tests/
	uv run black app/ servers/ tests/

mypy:
	uv run mypy app/ servers/
