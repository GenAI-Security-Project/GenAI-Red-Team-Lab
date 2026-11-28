PODMAN ?= podman
IMAGE ?= rag-chroma-config-ordering
CONTAINER ?= rag_chroma_config_ordering
PORT ?= 8000
TOKEN ?= test-token
AUTHN ?= chromadb.auth.token_authn.TokenAuthenticationServerProvider

.PHONY: all build up stop down attack clean help

help:
	@echo "Targets: build, up, attack, stop, down, clean"
	@echo "Docker works too: make PODMAN=docker all"

all: build up attack

build:
	$(PODMAN) build -t $(IMAGE) -f Containerfile .

up:
	@mkdir -p evidence
	$(PODMAN) run -d --name $(CONTAINER) -p 127.0.0.1:$(PORT):8000 \
		-e CHROMA_SERVER_AUTHN_PROVIDER=$(AUTHN) \
		-e CHROMA_SERVER_AUTHN_CREDENTIALS=$(TOKEN) \
		-e CHROMA_AUTH_TOKEN_TRANSPORT_HEADER=Authorization \
		-e MARKER_PATH=/evidence/marker.json \
		-e ANONYMIZED_TELEMETRY=FALSE \
		-v $(CURDIR)/evidence:/evidence \
		$(IMAGE)

stop:
	-$(PODMAN) stop $(CONTAINER)

down: stop
	-$(PODMAN) rm $(CONTAINER)

attack:
	$(PODMAN) exec $(CONTAINER) python /app/exploit/attack.py

clean: down
	-$(PODMAN) rmi $(IMAGE)
