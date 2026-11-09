PYTHON ?= python3
SANDBOX_NAME := agentic_local_skill_runtime
EXPLOIT_DIR := ../../exploitation/agentic_skill_poisoning
CONTAINER_ENGINE ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)
IMAGE := $(SANDBOX_NAME)

.PHONY: help build image container-run up down stop test-unit attack all format clean

help:
	@echo "Agentic Local Skill Runtime - targets:"
	@echo "  make build      - compile the standard-library runtime"
	@echo "  make image      - build the isolated runtime container"
	@echo "  make container-run SKILL_DIR=... - run one mounted skill with no network"
	@echo "  make up/down/stop - describe one-shot container operation"
	@echo "  make test-unit  - test filesystem boundaries and record-only tools"
	@echo "  make attack     - delegate the evaluation matrix to exploitation/"
	@echo "  make all        - run sandbox tests and exploitation matrix"
	@echo "  make format     - format the runtime and unit tests"
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

format:
	uvx isort --profile black app tests && uvx black app tests

clean:
	$(PYTHON) -c 'import shutil; from pathlib import Path; [shutil.rmtree(p) for p in Path(".").rglob("__pycache__")]'
