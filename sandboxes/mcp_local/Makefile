.PHONY: help install sync lock build up down test test-client test-mcp test-unit ollama-pull ollama-serve run-gradio-headless stop-gradio run-mcp stop-mcp format mypy clean

# Default target
help:
	@echo "LLM Mock API Template - Available Commands:"
	@echo ""
	@echo "  make build                 - Build the container image"
	@echo "  make up                    - Run the built container"
	@echo "  make down                  - Stop and remove the container"
	@echo "  make test                  - Test the health endpoint"
	@echo "  make test-client           - Run automated prompt tests against basic LLM endpoint"
	@echo "  make test-mcp              - Run automated prompt tests against MCP server (tool calling)"
	@echo "  make test-unit             - Run pytest unit & regression tests"
	@echo "  make clean                 - Clean up containers and images"
	@echo ""
	@echo "  make install               - Install uv package manager"
	@echo "  make sync                  - Sync/install project dependencies"
	@echo "  make lock                  - Update dependency lock file"
	@echo ""
	@echo "  make run-gradio-headless   - Full setup: sync, lock, clean, build, start server, and launch UI"
	@echo "                               (requires Ollama to be running first)"
	@echo "  make stop-gradio           - Stop the Gradio container"
	@echo ""
	@echo "  make format                - Run black and isort formatters"
	@echo "  make mypy                  - Run mypy static type checker"
	@echo ""
	@echo "  make ollama-pull           - Pull gpt-oss:20b model for Ollama"
	@echo "  make ollama-serve          - Start Ollama server"
	@echo ""
	@echo "Environment:"
	@echo "  - Ensure Ollama is running locally (port 11434)"
	@echo "  - Mock API key: sk-mock-key"
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
	podman build -f Containerfile -t app_container_build .
	# Create a network for the containers
	@echo "🌐 Creating network..."
	-podman network create --driver bridge sec_test_net 2>/dev/null || true

up:
	@echo "🚀 Starting container..."
	podman run -d --name app_container -p 8000:8000 -v ./data:/app/data --network sec_test_net app_container_build 
	@echo "✅ Container started!"

down:
	@echo "🛑 Stopping container..."
	podman rm -f app_container
	@echo "🌐 Removing network..."
	-podman network rm sec_test_net 2>/dev/null || true
	@echo "✅ Container stopped and network removed!"

clean:
	@echo "🧹 Cleaning up containers and images..."
	-podman rm -f app_container 2>/dev/null || true
	-podman rmi app_container_build 2>/dev/null || true
	@echo "✅ Cleanup complete!"

ollama-pull:
	ollama pull gpt-oss:20b

ollama-serve:
	@echo "🔍 Checking if Ollama is running..."
	@if lsof -Pi :11434 -sTCP:LISTEN -t >/dev/null 2>&1; then \
		echo "✅ Ollama is already running on port 11434"; \
	else \
		echo "🚀 Starting Ollama server..."; \
		ollama serve; \
	fi

format:
	@echo "Running black formatter..."
	uv run black app/ client/
	@echo "Running isort import sorter..."
	uv run isort app/ client/
	@echo "✅ Formatting complete!"

mypy:
	@echo "Running mypy type checker..."
	uv run mypy app/ client/
	@echo "✅ Type checking complete!"

test: sync lock clean ollama-pull ollama-serve build up
	@echo "⏳ Waiting for server to start..."
	@sleep 3
	@curl -s http://localhost:8000/health | grep ok && echo " ✅ Server is healthy!"

test-client: sync lock clean ollama-pull ollama-serve build up test
	podman exec app_container uv run python client/main.py

test-mcp: sync lock clean ollama-pull ollama-serve build up test run-mcp
	@echo "⏳ Waiting for MCP server and tool endpoint to be ready..."
	@sleep 3
	@echo "🧪 Running automated prompt tests against MCP server (tool calling)..."
	podman exec -e OPENAI_BASE_URL="http://localhost:8000/v1/tool" app_container uv run python client/main.py

test-unit: sync
	@echo "🧪 Running pytest unit & regression tests..."
	PYTHONPATH=. uv run pytest tests/


run-gradio-headless: sync lock clean ollama-pull ollama-serve build up test test-client run-mcp
	@echo "🧹 Stopping any existing Gradio instance..."
	@-podman rm -f gradio_container 2>/dev/null || true
	@echo "🚀 Starting Gradio interface (containerized)..."
	@podman run -d --name gradio_container \
		--network sec_test_net \
		-p 7860:7860 \
		-e OPENAI_BASE_URL="http://app_container:8000/v1" \
		--entrypoint uv \
		app_container_build \
		run python client/gradio_app.py
	@echo "✅ Gradio started in container 'gradio_container' on port 7860"

stop-gradio:
	@echo "🛑 Stopping Gradio..."
	@-podman rm -f gradio_container 2>/dev/null || true
	@echo "✅ Gradio stopped!"

run-mcp:
	@echo "🧹 Stopping any existing Gradio instance..."
	@-podman rm -f mcp_container 2>/dev/null || true
	@echo "🚀 Starting MCP server (containerized)..."
	@podman run -d --name mcp_container \
		--replace --network sec_test_net \
		 --entrypoint uv \
		 app_container_build \
		 run python mcp/main.py
	@echo "✅ MCP Server started in container 'mcp_container'"

stop-mcp:
	@echo "🛑 Stopping MCP Server..."
	@-podman rm -f mcp_container 2>/dev/null || true
	@echo "✅ MCP Server stopped!"