PODMAN ?= podman
IMAGE ?= rag-permissions-sandbox
CONTAINER ?= rag_permissions_container
PORT ?= 8000

.PHONY: all build up stop down attack test format clean help

help:
	@echo "Targets: build, up, stop, down, attack, test, format, clean"
	@echo "Tests and the attack script run without a container (uv + pytest)."

all: build up attack

build:
	$(PODMAN) build -t $(IMAGE) -f Containerfile .

up:
	$(PODMAN) run -d --name $(CONTAINER) -p 127.0.0.1:$(PORT):8000 $(IMAGE)

stop:
	-$(PODMAN) stop $(CONTAINER)

down: stop
	-$(PODMAN) rm $(CONTAINER)

clean: down
	-$(PODMAN) rmi $(IMAGE)

attack:
	uv run python client/attack.py

test:
	uv run pytest -q

format:
	uvx isort --profile black . && uvx black .
