CONTAINER_ENGINE := $(shell command -v podman 2> /dev/null || echo docker)

.PHONY: build-stage0 build-stage1 build-stage2 build-stage3 build-stage4 attack stop all clean logs health

build-stage0:
	@echo "Building Stage 0: langchain-core==1.2.24 (Unhardened)"
	$(CONTAINER_ENGINE) build -t langchain-stage0 -f Containerfile.stage0 .

build-stage1:
	@echo "Building Stage 1: langchain-core==1.2.25 (Incomplete Patch)"
	$(CONTAINER_ENGINE) build -t langchain-stage1 -f Containerfile.stage1 .

build-stage2:
	@echo "Building Stage 2: langchain-core==1.2.26 (Read-side Patched)"
	$(CONTAINER_ENGINE) build -t langchain-stage2 -f Containerfile.stage2 .

build-stage3:
	@echo "Building Stage 3: langchain-core==1.2.27 (Post-Fix)"
	$(CONTAINER_ENGINE) build -t langchain-stage3 -f Containerfile.stage3 .

build-stage4:
	@echo "Building Stage 4: langchain-core==latest (Latest)"
	$(CONTAINER_ENGINE) build -t langchain-stage4 -f Containerfile.stage4 .

build: build-stage0 build-stage1 build-stage2 build-stage3 build-stage4

attack-stage0: build-stage0
	$(CONTAINER_ENGINE) run -d --name langchain-sandbox -p 8000:8000 langchain-stage0
	@echo "Stage 0 (Unhardened) listening at http://localhost:8000"

attack-stage1: build-stage1
	$(CONTAINER_ENGINE) run -d --name langchain-sandbox -p 8001:8000 langchain-stage1
	@echo "Stage 1 (Incomplete Patch) listening at http://localhost:8001"

attack-stage2: build-stage2
	$(CONTAINER_ENGINE) run -d --name langchain-sandbox -p 8002:8000 langchain-stage2
	@echo "Stage 2 (Read-side Patched) listening at http://localhost:8002"

attack-stage3: build-stage3
	$(CONTAINER_ENGINE) run -d --name langchain-sandbox -p 8003:8000 langchain-stage3
	@echo "Stage 3 (Post-Fix) listening at http://localhost:8003"

attack-stage4: build-stage4
	$(CONTAINER_ENGINE) run -d --name langchain-sandbox -p 8004:8000 langchain-stage4
	@echo "Stage 4 (Latest) listening at http://localhost:8004"

attack: attack-stage0

stop:
	-$(CONTAINER_ENGINE) stop langchain-sandbox 2>/dev/null
	-$(CONTAINER_ENGINE) rm langchain-sandbox 2>/dev/null

all: build

clean: stop
	-$(CONTAINER_ENGINE) rmi langchain-stage0 2>/dev/null
	-$(CONTAINER_ENGINE) rmi langchain-stage1 2>/dev/null
	-$(CONTAINER_ENGINE) rmi langchain-stage2 2>/dev/null
	-$(CONTAINER_ENGINE) rmi langchain-stage3 2>/dev/null
	-$(CONTAINER_ENGINE) rmi langchain-stage4 2>/dev/null

logs:
	$(CONTAINER_ENGINE) logs -f langchain-sandbox

health:
	@curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "Target unreachable."

