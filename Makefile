# Makefile for brain-llm.
# Usage: `make help` lists all available targets.

PYTHON       ?= python3
PIP          ?= $(PYTHON) -m pip
VENV         ?= .venv
VENV_BIN     := $(VENV)/bin
UVICORN      := $(VENV_BIN)/uvicorn
APP_MODULE   := app.main:app
APP_HOST     ?= 0.0.0.0
APP_PORT     ?= 8000
LOG_LEVEL    ?= INFO
DOCKER       ?= docker
COMPOSE      ?= $(DOCKER) compose
IMAGE_NAME   ?= brain-llm:latest

.DEFAULT_GOAL := help

.PHONY: help venv install run dev test lint clean \
        docker-build docker-up docker-down docker-logs \
        postman

help:  ## Show this help message.
	@awk 'BEGIN {FS = ":.*##"; printf "\nAvailable targets:\n"} \
	/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

venv:  ## Create a local Python virtual environment.
	$(PYTHON) -m venv $(VENV)

install: venv  ## Install Python dependencies into the virtual environment.
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -r requirements.txt

run:  ## Run the API with uvicorn (production-ish).
	LOG_LEVEL=$(LOG_LEVEL) $(UVICORN) $(APP_MODULE) --host $(APP_HOST) --port $(APP_PORT)

dev:  ## Run the API with auto-reload for development.
	LOG_LEVEL=DEBUG $(UVICORN) $(APP_MODULE) --host $(APP_HOST) --port $(APP_PORT) --reload

test:  ## Run the test suite (pytest).
	$(VENV_BIN)/pytest -q

lint:  ## Run basic lint checks.
	$(VENV_BIN)/python -m compileall -q app

clean:  ## Remove caches and build artifacts.
	rm -rf $(VENV) .pytest_cache __pycache__ **/__pycache__ *.egg-info data/brain_llm.db

docker-build:  ## Build the Docker image.
	$(DOCKER) build -t $(IMAGE_NAME) .

docker-up:  ## Start the full stack via docker compose.
	$(COMPOSE) up -d --build

docker-down:  ## Stop and remove the docker compose stack.
	$(COMPOSE) down

docker-logs:  ## Tail logs of the brain-llm container.
	$(COMPOSE) logs -f brain-llm

postman:  ## Download the generated Postman collection to ./brain-llm.postman_collection.json.
	curl -fsSL http://$(APP_HOST):$(APP_PORT)/api/v1/postman/collection -o brain-llm.postman_collection.json
