.PHONY: help build up down clean logs n8n

# Default target
help:
	@echo "n8n Sandbox (CVE-2026-21877) - Available Commands:"
	@echo ""
	@echo "  make n8n           - Full setup: clean, build, and start n8n"
	@echo "  make build         - Build the container image"
	@echo "  make up            - Run the container"
	@echo "  make down          - Stop and remove the container"
	@echo "  make logs          - View container logs"
	@echo "  make clean         - Clean up containers and images"
	@echo ""
	@echo "Environment:"
	@echo "  - n8n version: 1.120.0"
	@echo "  - URL: http://localhost:5678"
	@echo "  - Vulnerability: CVE-2026-21877 (RCE via Arbitrary File Write)"
	@echo ""

build:
	@echo "🔨 Building container image..."
	podman build -f Containerfile -t n8n_vuln_build .
	# Create a network for the containers if needed (reusing the one from llm_local or creating new)
	@echo "🌐 Creating network..."
	-podman network create --driver bridge sec_test_net 2>/dev/null || true

up:
	@echo "🚀 Starting container..."
	@mkdir -p data
	# N8N_HOST=0.0.0.0 and defaults to ensure it's accessible.
	# NODES_EXCLUDE="" to ensure all nodes (including vulnerable/dangerous ones) are active.
	podman run -d --name n8n_vuln_container \
		-p 5678:5678 \
		--network sec_test_net \
		-v ./data:/home/node/.n8n \
		-e N8N_HOST=0.0.0.0 \
		-e N8N_PORT=5678 \
		-e WEBHOOK_URL=http://localhost:5678/ \
		-e NODES_EXCLUDE="" \
		n8n_vuln_build
	@echo "✅ Container started at http://localhost:5678"

down:
	@echo "🛑 Stopping container..."
	podman rm -f n8n_vuln_container
	@echo "✅ Container stopped!"

clean:
	@echo "🧹 Cleaning up containers and images..."
	-podman rm -f n8n_vuln_container 2>/dev/null || true
	-podman rmi n8n_vuln_build 2>/dev/null || true
	-podman network rm sec_test_net 2>/dev/null || true
	rm -rf data/database.sqlite
	@echo "✅ Cleanup complete!"

logs:
	podman logs -f n8n_vuln_container

n8n: clean build up wait seed
	@echo "✅ n8n is running. Access it at http://localhost:5678"

sync:
	uv sync

lock:
	uv lock

wait:
	@echo "⏳ Waiting for n8n to initialize database..."
	@timeout=60; \
	while ! uv run curl -s http://localhost:5678 > /dev/null; do \
		sleep 2; \
		timeout=$$((timeout-2)); \
		if [ $$timeout -le 0 ]; then echo "❌ Timed out waiting for n8n"; exit 1; fi; \
	done
	@echo "✅ n8n is reachable (DB should be initialized)."
	@sleep 5

seed:
	@echo "🌱 Seeding database with admin user..."
	uv run python3 seed_user.py

format:
	@echo "🎨 Formatting Python files..."
	uv run black .
	uv run isort .
	uv run mypy .

