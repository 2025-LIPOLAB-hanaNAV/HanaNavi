# Ensure compose reads envs from project root .env
COMPOSE = docker compose --env-file .env -f docker/docker-compose.yml

.PHONY: up down ps logs build rebuild build-apis build-ui up-rag up-etl restart pull-model pull-model-local shell-ollama
 .PHONY: config

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down -v

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f --tail=100

build:
	$(COMPOSE) build

rebuild:
	$(COMPOSE) build --no-cache

build-apis:
	$(COMPOSE) build rag-api etl-api eval-api worker

build-apis-offline:
	$(COMPOSE) build --build-arg OFFLINE=1 rag-api etl-api eval-api worker

build-ui:
	$(COMPOSE) build board chatbot

up-rag:
	$(COMPOSE) up -d rag-api

up-etl:
	$(COMPOSE) up -d etl-api

restart:
	$(COMPOSE) up -d --no-deps --build $(service)

MODEL ?= gemma3:12b
pull-model:
	$(COMPOSE) exec ollama ollama pull $(MODEL)

pull-model-local:
	ollama pull $(MODEL)

shell-ollama:
	$(COMPOSE) exec ollama bash -lc "ollama list || true"

config:
	$(COMPOSE) config

.PHONY: wheels-worker wheels-rag wheels-etl wheels-eval wheels-all
wheels-worker:
	docker run --rm -v $$PWD:/work -w /work python:3.11-slim bash -lc "pip install -U pip wheel && pip download -r requirements/worker.txt -d vendor/wheels/worker --only-binary=:all: || true"
wheels-rag:
	docker run --rm -v $$PWD:/work -w /work python:3.11-slim bash -lc "pip install -U pip wheel && pip download -r requirements/rag-api.txt -d vendor/wheels/rag-api --only-binary=:all: || true"
wheels-etl:
	docker run --rm -v $$PWD:/work -w /work python:3.11-slim bash -lc "pip install -U pip wheel && pip download -r requirements/etl-api.txt -d vendor/wheels/etl-api --only-binary=:all: || true"
wheels-eval:
	docker run --rm -v $$PWD:/work -w /work python:3.11-slim bash -lc "pip install -U pip wheel && pip download -r requirements/eval-api.txt -d vendor/wheels/eval-api --only-binary=:all: || true"
wheels-all: wheels-worker wheels-rag wheels-etl wheels-eval

.PHONY: seed-sample
seed-sample:
	bash scripts/seed_sample.sh

.PHONY: seed-sample-pdf
seed-sample-pdf:
	bash scripts/seed_sample_pdf.sh $(ARGS)

.PHONY: reindex-opensearch
reindex-opensearch:
	$(COMPOSE) exec worker python -m app.tools.reindex_opensearch || true

.PHONY: opensearch-setup
opensearch-setup:
	$(COMPOSE) exec worker python -m app.tools.setup_opensearch || true
