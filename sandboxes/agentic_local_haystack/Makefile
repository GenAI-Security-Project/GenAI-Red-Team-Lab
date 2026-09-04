CONTAINER_ENGINE := $(shell command -v podman 2> /dev/null || echo docker)
PORT ?= 8000

.PHONY: all build attack stop clean logs health

all: attack

build:
	@echo "Building Haystack sandbox (haystack-ai==2.27.0)..."
	$(CONTAINER_ENGINE) build -t haystack-sandbox -f Containerfile .

attack: build
	-$(CONTAINER_ENGINE) stop haystack-sandbox 2>/dev/null
	-$(CONTAINER_ENGINE) rm haystack-sandbox 2>/dev/null
	$(CONTAINER_ENGINE) run -d --name haystack-sandbox -p $(PORT):8000 haystack-sandbox
	@echo "Waiting for service initialization..."
	@sleep 2
	@echo "Haystack sandbox listening at http://localhost:$(PORT)"

stop:
	-$(CONTAINER_ENGINE) stop haystack-sandbox 2>/dev/null
	-$(CONTAINER_ENGINE) rm haystack-sandbox 2>/dev/null

clean: stop
	-$(CONTAINER_ENGINE) rmi haystack-sandbox 2>/dev/null

logs:
	$(CONTAINER_ENGINE) logs -f haystack-sandbox

health:
	@curl -s http://localhost:$(PORT)/health | python3 -m json.tool 2>/dev/null || echo "Target unreachable."
