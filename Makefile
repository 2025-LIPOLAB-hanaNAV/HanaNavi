COMPOSE = docker compose -f docker/docker-compose.yml

.PHONY: up down ps logs build pull-model

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down -v

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f --tail=100

build:
	$(COMPOSE) build --no-cache

MODEL ?= gemma3:12b
pull-model:
	$(COMPOSE) exec ollama ollama pull $(MODEL)
