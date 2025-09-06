COMPOSE = docker compose -f docker/docker-compose.yml

.PHONY: up down ps logs build rebuild build-apis build-ui up-rag up-etl restart pull-model pull-model-local shell-ollama

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
