PYTHON ?= python3
CONTAINER ?= podman
MODE ?= hardened
IMAGE ?= tenant-isolation-lab:local
NAME ?= tenant-isolation-lab
PORT ?= 8765

.PHONY: all build up test stop run-local

all: build up

build:
	$(CONTAINER) build -f Containerfile -t $(IMAGE) .

up:
	$(CONTAINER) run -d --rm --name $(NAME) \
		-p 127.0.0.1:$(PORT):8000 -e LAB_MODE=$(MODE) $(IMAGE)

test:
	$(PYTHON) -m unittest discover -s tests -v

run-local:
	$(PYTHON) -m app.server --mode $(MODE) --port $(PORT)

stop:
	-$(CONTAINER) stop $(NAME)
