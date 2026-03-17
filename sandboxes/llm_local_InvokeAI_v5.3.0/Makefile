IMAGE_NAME     := invokeai
CONTAINER_NAME := invokeai
PORT           := 9090
NETWORK        := podman

.PHONY: all build run stop clean ip

all: build run

build:
	podman build -f Containerfile -t $(IMAGE_NAME) .

run:
	podman run -d \
		--name $(CONTAINER_NAME) \
		--network host \
		-p $(PORT):$(PORT) \
		$(IMAGE_NAME)
	@echo ""
	@echo "  [+] InvokeAI v5.3.0 running at http://localhost:$(PORT)"
	@echo "  [+] CVE-2024-12029 (RCE via model deserialization) is exploitable."
	@echo "  [+] Container IP (use this for --ip when attacking):"
	@podman inspect $(CONTAINER_NAME) \
		--format '{{range .NetworkSettings.Networks}}  [+] Container IP : {{.IPAddress}}{{end}}'
	@echo ""

ip:
	@podman inspect $(CONTAINER_NAME) \
		--format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

stop:
	podman stop $(CONTAINER_NAME) 2>/dev/null || true
	podman rm   $(CONTAINER_NAME) 2>/dev/null || true

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
