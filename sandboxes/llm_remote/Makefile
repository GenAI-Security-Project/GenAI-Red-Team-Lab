.PHONY: help install sync lock build up down test test-client test-unit run-gradio-headless stop-gradio format mypy clean

# Container and image identifiers
IMAGE_NAME ?= app_remote_container_build
CONTAINER_NAME ?= app_remote_container
GRADIO_CONTAINER_NAME ?= gradio_remote_container
NETWORK_NAME ?= sec_remote_test_net

# Pass environment variables into containers if set on host
ENV_FORWARD = \
	-e OPENAI_API_KEY \
	-e OPENAI_BASE_URL \
	-e ANTHROPIC_API_KEY \
	-e ANTHROPIC_AUTH_TOKEN \
	-e ANTHROPIC_BASE_URL \
	-e GEMINI_API_KEY \
	-e GOOGLE_API_KEY \
	-e MISTRAL_API_KEY \
	-e MISTRAL_BASE_URL \
	-e OPENROUTER_API_KEY \
	-e OPENROUTER_BASE_URL \
	-e TRUEFOUNDRY_API_KEY \
	-e TFY_API_KEY \
	-e TRUEFOUNDRY_BASE_URL \
	-e TFY_BASE_URL \
	-e LLM_VENDOR \
	-e LLM_MODEL \
	-e SANDBOX_API_KEY

MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
ENV_FILE := $(MAKEFILE_DIR).env
ENV_FILE_FLAG ?= $(shell [ -f $(ENV_FILE) ] && echo "--env-file $(ENV_FILE)")

# Default target
help:
	@echo "LLM Remote Sandbox - Available Commands:"
	@echo ""
	@echo "  make build                 - Build the container image"
	@echo "  make up                    - Run the built container"
	@echo "  make down                  - Stop and remove the container"
	@echo "  make test                  - Test the health endpoint"
	@echo "  make test-client           - Run automated prompt tests from config/prompts.toml"
	@echo "  make test-unit             - Run pytest unit and integration tests"
	@echo "  make clean                 - Clean up containers and images"
	@echo ""
	@echo "  make install               - Install uv package manager"
	@echo "  make sync                  - Sync/install project dependencies"
	@echo "  make lock                  - Update dependency lock file"
	@echo ""
	@echo "  make run-gradio-headless   - Full setup: sync, lock, clean, build, start server, and launch UI"
	@echo "  make stop-gradio           - Stop the Gradio container"
	@echo ""
	@echo "  make format                - Run black and isort formatters"
	@echo "  make mypy                  - Run mypy static type checker"
	@echo ""
	@echo "Environment:"
	@echo "  - Export at least one vendor API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, etc.)"
	@echo "  - (Optional) Set LLM_VENDOR to pin provider: openai | anthropic | gemini | mistral | openrouter | truefoundry"
	@echo "  - API endpoint: http://localhost:8000"
	@echo ""

install:
	pip install uv

sync:
	uv sync

lock:
	uv lock

build:
	@echo "🔨 Building container image..."
	podman build -f Containerfile -t $(IMAGE_NAME) .
	@echo "🌐 Creating network..."
	-podman network create --driver bridge $(NETWORK_NAME) 2>/dev/null || true

up:
	@echo "🚀 Starting remote sandbox container..."
	podman run -d --name $(CONTAINER_NAME) \
		-p 8000:8000 \
		--network $(NETWORK_NAME) \
		$(ENV_FILE_FLAG) \
		$(ENV_FORWARD) \
		$(IMAGE_NAME)
	@echo "✅ Container started!"

down:
	@echo "🛑 Stopping container..."
	-podman rm -f $(CONTAINER_NAME) 2>/dev/null || true
	@echo "🌐 Removing network..."
	-podman network rm $(NETWORK_NAME) 2>/dev/null || true
	@echo "✅ Container stopped and network removed!"

clean:
	@echo "🧹 Cleaning up containers and images..."
	-podman rm -f $(CONTAINER_NAME) 2>/dev/null || true
	-podman rm -f $(GRADIO_CONTAINER_NAME) 2>/dev/null || true
	-podman network rm $(NETWORK_NAME) 2>/dev/null || true
	-podman rmi $(IMAGE_NAME) 2>/dev/null || true
	@echo "✅ Cleanup complete!"

format:
	@echo "Running isort import sorter..."
	uv run isort app/ client/
	@echo "Running black formatter..."
	uv run black app/ client/
	@echo "✅ Formatting complete!"

mypy:
	@echo "Running mypy type checker..."
	uv run mypy app/ client/
	@echo "✅ Type checking complete!"

test: sync lock clean build up
	@echo "⏳ Waiting for server to start..."
	@for i in $$(seq 1 30); do \
		curl -sf http://localhost:8000/health >/dev/null 2>&1 && break; \
		sleep 1; \
	done
	@curl -s http://localhost:8000/health | grep -q "ok" && echo " ✅ Server is healthy!" || echo " ⚠️ Health check response: $$(curl -s http://localhost:8000/health)"

test-client: sync lock clean build up test
	podman exec $(CONTAINER_NAME) uv run python client/main.py

test-unit:
	uv run pytest

run-gradio-headless: sync lock clean build up test
	@echo "🧹 Stopping any existing Gradio instance..."
	@-podman rm -f $(GRADIO_CONTAINER_NAME) 2>/dev/null || true
	@echo "🚀 Starting Gradio interface (containerized)..."
	@podman run -d --name $(GRADIO_CONTAINER_NAME) \
		--network $(NETWORK_NAME) \
		-p 7860:7860 \
		-e SANDBOX_API_URL="http://$(CONTAINER_NAME):8000" \
		-e SANDBOX_API_KEY="sk-mock-key" \
		-e NO_PROXY="host.containers.internal,$(CONTAINER_NAME)" \
		-e no_proxy="host.containers.internal,$(CONTAINER_NAME)" \
		$(ENV_FILE_FLAG) \
		$(ENV_FORWARD) \
		--entrypoint uv \
		$(IMAGE_NAME) \
		run python client/gradio_app.py
	@echo "✅ Gradio started in container '$(GRADIO_CONTAINER_NAME)' on port 7860"

stop-gradio:
	@echo "🛑 Stopping Gradio..."
	@-podman rm -f $(GRADIO_CONTAINER_NAME) 2>/dev/null || true
	@echo "✅ Gradio stopped!"
