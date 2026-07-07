CONTAINER_ENGINE := $(shell command -v podman 2> /dev/null || echo docker)

.PHONY: stop attack health build

build:
	$(CONTAINER_ENGINE) build -t sk-vulnerable -f Containerfile .

attack: stop build
	$(CONTAINER_ENGINE) run -d --name sk-vulnerable -p 8000:8000 -v ./app/data:/app/data sk-vulnerable
	@echo "Sandbox running at http://localhost:8000"

stop:
	-$(CONTAINER_ENGINE) stop sk-vulnerable 2>/dev/null
	-$(CONTAINER_ENGINE) rm sk-vulnerable 2>/dev/null

health:
	@curl -s http://localhost:8000/api/health | jq . 2>/dev/null || echo "Service not reachable"
