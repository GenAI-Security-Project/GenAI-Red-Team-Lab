PYTHON ?= python3
CONTAINER ?= podman
MODE ?= hardened
IMAGE ?= tenant-isolation-lab:local
NAME ?= tenant-isolation-lab
PORT ?= 8765

.PHONY: all build up attack test stop run-local

all: build up

build:
	$(CONTAINER) build -f Containerfile -t $(IMAGE) .

up:
	$(CONTAINER) run -d --rm --name $(NAME) \
		-p 127.0.0.1:$(PORT):8000 -e LAB_MODE=$(MODE) $(IMAGE)

attack:
	$(PYTHON) ../../exploitation/tenant_isolation/probe.py \
		--url http://127.0.0.1:$(PORT) --expect-mode $(MODE)

test:
	$(PYTHON) -m unittest discover -s tests -v

run-local:
	$(PYTHON) -m app.server --mode $(MODE) --port $(PORT)

stop:
	-$(CONTAINER) stop $(NAME)
