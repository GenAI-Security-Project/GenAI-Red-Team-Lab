PYTHON ?= python3
EXPLOIT_DIR := ../../exploitation/agentic_skill_poisoning
CONTAINER_ENGINE ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)
IMAGE := agentic-local-skill-runtime

.PHONY: help build image container-run up down stop test-unit attack all clean

help:
	@echo "Agentic Local Skill Runtime - targets:"
	@echo "  make build      - compile the standard-library runtime"
	@echo "  make image      - build the isolated runtime container"
	@echo "  make container-run SKILL_DIR=... - run one mounted skill with no network"
	@echo "  make test-unit  - test filesystem boundaries and record-only tools"
	@echo "  make attack     - delegate the evaluation matrix to exploitation/"
	@echo "  make clean      - remove generated Python caches"

build:
	$(PYTHON) -m compileall -q app

image:
	$(CONTAINER_ENGINE) build -t $(IMAGE) -f Containerfile .

container-run:
	@test -n "$(SKILL_DIR)" || (echo "Set SKILL_DIR to a directory containing SKILL.md" && exit 1)
	$(CONTAINER_ENGINE) run --rm --network none -v "$(abspath $(SKILL_DIR)):/skills:ro" $(IMAGE) --skill-dir /skills

up down stop:
	@echo "This runtime is a one-shot CLI; use make container-run SKILL_DIR=..."

test-unit:
	PYTHONPATH=../../ $(PYTHON) -m unittest discover -s tests -v

attack:
	$(MAKE) -C $(EXPLOIT_DIR) attack

all: test-unit attack

clean:
	@echo "Generated Python caches are ignored by Git."
