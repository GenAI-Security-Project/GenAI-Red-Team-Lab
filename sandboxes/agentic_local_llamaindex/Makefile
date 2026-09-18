CONTAINER_ENGINE := $(shell command -v podman 2> /dev/null || echo docker)

.PHONY: attack all attack-stage0 attack-stage1 attack-stage2 attack-stage3 stop clean logs health verify

# Default attack target (runs Stage 0)
attack: attack-stage0

# Run all stages sequentially
all: attack-stage0 attack-stage1 attack-stage2 attack-stage3

attack-stage0:
	@echo "Building Stage 0: llama-index-core v0.14.19 (Original Vulnerable)"
	$(CONTAINER_ENGINE) build -t llamaindex-sandbox-stage0 -f Containerfile.stage0 .
	-$(CONTAINER_ENGINE) stop llamaindex-sandbox 2>/dev/null
	-$(CONTAINER_ENGINE) rm llamaindex-sandbox 2>/dev/null
	-fuser -k 8000/tcp 2>/dev/null || true
	$(CONTAINER_ENGINE) run -d --name llamaindex-sandbox -p 8000:8000 llamaindex-sandbox-stage0
	@echo "Waiting for API to be ready..."
	@for i in $$(seq 1 15); do \
		if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
			echo "Stage 0 ready at http://localhost:8000"; \
			echo "Warming up POST handler..."; \
			curl -sf -X POST http://localhost:8000/chat \
			  -H "Content-Type: application/json" \
			  -d '{"query": "stage"}' > /dev/null 2>&1 || true; \
			sleep 1; \
			exit 0; \
		fi; \
		echo "  attempt $$i/15..."; \
		sleep 2; \
	done; \
	echo "ERROR: API did not become ready in time"; \
	exit 1

attack-stage1:
	@echo "Building Stage 1: llama-index-core v0.14.20 (dataset.py Deleted)"
	$(CONTAINER_ENGINE) build -t llamaindex-sandbox-stage1 -f Containerfile.stage1 .
	-$(CONTAINER_ENGINE) stop llamaindex-sandbox 2>/dev/null
	-$(CONTAINER_ENGINE) rm llamaindex-sandbox 2>/dev/null
	-fuser -k 8000/tcp 2>/dev/null || true
	$(CONTAINER_ENGINE) run -d --name llamaindex-sandbox -p 8000:8000 llamaindex-sandbox-stage1
	@echo "Waiting for API to be ready..."
	@for i in $$(seq 1 15); do \
		if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
			echo "Stage 1 ready at http://localhost:8000"; \
			echo "Warming up POST handler..."; \
			curl -sf -X POST http://localhost:8000/chat \
			  -H "Content-Type: application/json" \
			  -d '{"query": "stage"}' > /dev/null 2>&1 || true; \
			sleep 1; \
			exit 0; \
		fi; \
		echo "  attempt $$i/15..."; \
		sleep 2; \
	done; \
	echo "ERROR: API did not become ready in time"; \
	exit 1

attack-stage2:
	@echo "Building Stage 2: llama-index-core v0.14.21+ (Logic Migrated)"
	$(CONTAINER_ENGINE) build -t llamaindex-sandbox-stage2 -f Containerfile.stage2 .
	-$(CONTAINER_ENGINE) stop llamaindex-sandbox 2>/dev/null
	-$(CONTAINER_ENGINE) rm llamaindex-sandbox 2>/dev/null
	-fuser -k 8000/tcp 2>/dev/null || true
	$(CONTAINER_ENGINE) run -d --name llamaindex-sandbox -p 8000:8000 llamaindex-sandbox-stage2
	@echo "Waiting for API to be ready..."
	@for i in $$(seq 1 15); do \
		if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
			echo "Stage 2 ready at http://localhost:8000"; \
			echo "Warming up POST handler..."; \
			curl -sf -X POST http://localhost:8000/chat \
			  -H "Content-Type: application/json" \
			  -d '{"query": "stage"}' > /dev/null 2>&1 || true; \
			sleep 1; \
			exit 0; \
		fi; \
		echo "  attempt $$i/15..."; \
		sleep 2; \
	done; \
	echo "ERROR: API did not become ready in time"; \
	exit 1

attack-stage3:
	@echo "Building Stage 3: llama-index-core v0.14.21 + workflows v2.14.0 (data_sinks Patched)"
	$(CONTAINER_ENGINE) build -t llamaindex-sandbox-stage3 -f Containerfile.stage3 .
	-$(CONTAINER_ENGINE) stop llamaindex-sandbox 2>/dev/null
	-$(CONTAINER_ENGINE) rm llamaindex-sandbox 2>/dev/null
	-fuser -k 8000/tcp 2>/dev/null || true
	$(CONTAINER_ENGINE) run -d --name llamaindex-sandbox -p 8000:8000 llamaindex-sandbox-stage3
	@echo "Waiting for API to be ready..."
	@for i in $$(seq 1 15); do \
		if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
			echo "Stage 3 ready at http://localhost:8000"; \
			echo "Warming up POST handler..."; \
			curl -sf -X POST http://localhost:8000/chat \
			  -H "Content-Type: application/json" \
			  -d '{"query": "stage"}' > /dev/null 2>&1 || true; \
			sleep 1; \
			exit 0; \
		fi; \
		echo "  attempt $$i/15..."; \
		sleep 2; \
	done; \
	echo "ERROR: API did not become ready in time"; \
	exit 1

stop:
	-$(CONTAINER_ENGINE) stop llamaindex-sandbox 2>/dev/null
	-$(CONTAINER_ENGINE) rm llamaindex-sandbox 2>/dev/null
	-fuser -k 8000/tcp 2>/dev/null || true

clean: stop
	-$(CONTAINER_ENGINE) rmi llamaindex-sandbox-stage0 2>/dev/null
	-$(CONTAINER_ENGINE) rmi llamaindex-sandbox-stage1 2>/dev/null
	-$(CONTAINER_ENGINE) rmi llamaindex-sandbox-stage2 2>/dev/null
	-$(CONTAINER_ENGINE) rmi llamaindex-sandbox-stage3 2>/dev/null

logs:
	$(CONTAINER_ENGINE) logs -f llamaindex-sandbox

health:
	@curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "Target unreachable."

verify:
	@curl -s http://localhost:8000/verify | python3 -m json.tool 2>/dev/null || echo "Target unreachable."
