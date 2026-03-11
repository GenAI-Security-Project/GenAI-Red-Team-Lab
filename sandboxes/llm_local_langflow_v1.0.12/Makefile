IMAGE_NAME     := langflow
CONTAINER_NAME := langflow
PORT           := 7860
.PHONY: all build run stop attack clean logs
all: build run
build:
	podman build -f Containerfile -t $(IMAGE_NAME) .
run:
	@echo "[*] Starting $(CONTAINER_NAME) on port $(PORT)..."
	@podman stop $(CONTAINER_NAME) > /dev/null 2>&1 || true
	@podman rm   $(CONTAINER_NAME) > /dev/null 2>&1 || true
	@if ss -tlnp 2>/dev/null | grep -q ":$(PORT) " || lsof -i :$(PORT) > /dev/null 2>&1; then \
		echo "  [-] ERROR: Port $(PORT) is already in use by another process."; \
		echo "      Free the port before retrying (e.g. kill the process using it)."; \
		exit 1; \
	fi
	@if podman run -d \
		--name $(CONTAINER_NAME) \
		--network host \
		$(IMAGE_NAME) > /dev/null 2>&1; then \
		echo ""; \
		echo "  [+] Langflow v1.0.12 running at http://localhost:$(PORT)"; \
		echo ""; \
	else \
		echo "  [-] ERROR: Failed to start container."; \
		echo "      Check logs with: make logs"; \
		exit 1; \
	fi
attack: all
stop:
	podman stop $(CONTAINER_NAME) 2>/dev/null || true
	podman rm   $(CONTAINER_NAME) 2>/dev/null || true
logs:
	podman logs -f $(CONTAINER_NAME)
clean: stop
	podman rmi $(IMAGE_NAME) 2>/dev/null || true
format:
	@echo "[*] Running black formatter..."
	@if command -v uv >/dev/null 2>&1; then \
		uv run black $(shell find . -name "*.py") 2>/dev/null && echo "  [+] black done" || echo "  [-] black failed or no .py files found"; \
	elif command -v black >/dev/null 2>&1; then \
		black $(shell find . -name "*.py") 2>/dev/null && echo "  [+] black done" || echo "  [-] black failed or no .py files found"; \
	else \
		echo "  [-] black not found. Install with: pip install black"; \
	fi
	@echo "[*] Running isort import sorter..."
	@if command -v uv >/dev/null 2>&1; then \
		uv run isort $(shell find . -name "*.py") 2>/dev/null && echo "  [+] isort done" || echo "  [-] isort failed or no .py files found"; \
	elif command -v isort >/dev/null 2>&1; then \
		isort $(shell find . -name "*.py") 2>/dev/null && echo "  [+] isort done" || echo "  [-] isort failed or no .py files found"; \
	else \
		echo "  [-] isort not found. Install with: pip install isort"; \
	fi
	@echo "[+] Formatting complete!"

