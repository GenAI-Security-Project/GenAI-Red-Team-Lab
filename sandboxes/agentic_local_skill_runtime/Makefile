PYTHON ?= python3
EXPLOIT_DIR := ../../exploitation/agentic_skill_poisoning

.PHONY: help build up down stop test-unit attack all clean

help:
	@echo "Agentic Local Skill Runtime - targets:"
	@echo "  make build      - compile the standard-library runtime"
	@echo "  make test-unit  - test filesystem boundaries and record-only tools"
	@echo "  make attack     - delegate the evaluation matrix to exploitation/"
	@echo "  make clean      - remove generated Python caches"

build:
	$(PYTHON) -m compileall -q app

up down stop:
	@echo "The runtime is an in-process, record-only sandbox; no service to manage."

test-unit:
	PYTHONPATH=../../ $(PYTHON) -m unittest discover -s tests -v

attack:
	$(MAKE) -C $(EXPLOIT_DIR) attack

all: test-unit attack

clean:
	@echo "Generated Python caches are ignored by Git."
