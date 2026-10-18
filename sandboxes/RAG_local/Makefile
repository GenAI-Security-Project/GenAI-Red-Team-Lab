.PHONY: help install sync lock build up down test test-client ollama-pull ollama-serve gradio run-gradio-headless stop-gradio ingest upload format mypy clean

# Default target
help:
	@echo "LLM Mock API Template - Available Commands:"
	@echo ""
	@echo "  make build                 - Build the container image"
	@echo "  make up                    - Run the built container"
	@echo "  make down                  - Stop and remove the container"
	@echo "  make test                  - Test the health endpoint"
	@echo "  make test-client           - Run automated prompt tests from config/prompts.toml"
	@echo "  make clean                 - Clean up containers and images"
	@echo ""
	@echo "  make install               - Install uv package manager"
	@echo "  make sync                  - Sync/install project dependencies"
	@echo "  make lock                  - Update dependency lock file"
	@echo ""
	@echo "  make gradio                - Full setup: sync, lock, clean, build, start server, and launch UI (local)"
	@echo "  make run-gradio-headless   - Full setup: sync, lock, clean, build, start server, and launch UI (container)"
	@echo "  make stop-gradio           - Stop the Gradio container"
	@echo ""
	@echo "  make format                - Run black and isort formatters"
	@echo "  make mypy                  - Run mypy static type checker"
	@echo ""
	@echo "  make ollama-pull           - Pull gpt-oss:20b model for Ollama"
	@echo "  make ollama-serve          - Start Ollama server"
	@echo "  make ingest                - Ingest all PDFs from data/documents/"
	@echo "  make upload PATH=x         - Upload a file to data/documents/ (requires PATH argument)"
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
	ollama pull nomic-embed-text

ollama-serve:
	@echo "🔍 Checking if Ollama is running..."
	@if curl -sf http://localhost:11434/api/version >/dev/null 2>&1; then \
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
	@for i in $$(seq 1 30); do \
		curl -sf http://localhost:8000/health >/dev/null 2>&1 && break; \
		sleep 1; \
	done
	@curl -s http://localhost:8000/health | grep ok && echo " ✅ Server is healthy!"

test-client: sync lock clean ollama-pull ollama-serve build up test
	podman exec -e PYTHONWARNINGS="ignore::SyntaxWarning" app_container uv run python client/main.py

gradio: sync lock clean ollama-pull ollama-serve build up test test-client
	@echo "🧹 Stopping any existing Gradio instance..."
	@-lsof -ti:7860 | xargs kill -9 2>/dev/null || true
	@echo "🚀 Starting Gradio interface..."
	@uv run python client/gradio_app.py & sleep 3 && open http://localhost:7860

run-gradio-headless: sync lock clean ollama-pull ollama-serve build up test test-client
	@echo "🧹 Stopping any existing Gradio instance..."
	@-podman rm -f gradio_container 2>/dev/null || true
	@echo "🚀 Starting Gradio interface (containerized)..."
	@podman run -d --name gradio_container \
		--network sec_test_net \
		-p 7860:7860 \
		-e OPENAI_BASE_URL="http://app_container:8000/v1" \
		-e S3_BASE_URL="http://app_container:8000/s3" \
		-e PINECONE_BASE_URL="http://app_container:8000/pinecone" \
		-e NO_PROXY="host.containers.internal,app_container" \
		-e no_proxy="host.containers.internal,app_container" \
		--entrypoint uv \
		app_container_build \
		run python client/gradio_app.py
	@echo "✅ Gradio started in container 'gradio_container' on port 7860"

stop-gradio:
	@echo "🛑 Stopping Gradio..."
	@-podman rm -f gradio_container 2>/dev/null || true
	@echo "✅ Gradio stopped!"

ingest: sync lock clean build up
	@echo "Processing PDFs in data/documents/..."
	@podman exec -e OLLAMA_BASE_URL="http://host.containers.internal:11434/v1" app_container bash -c 'for f in data/documents/*.pdf; do \
		if [ -f "$$f" ]; then \
			echo "Ingesting $$f..."; \
			uv run python ETL/ingest.py "$$f"; \
		else \
			echo "No PDF files found in data/documents/"; \
		fi \
	done'

upload:
	@if [ -z "$(PATH)" ]; then \
		echo "❌ Error: PATH argument is required. Usage: make upload PATH=path/to/file"; \
		exit 1; \
	fi
	@echo "Uploading $(PATH) to S3 mock..."
	@curl -X PUT http://localhost:8000/s3/documents/$(shell basename $(PATH)) \
		-H "Api-Key: foobar" \
		--data-binary @$(PATH)
	@echo ""
