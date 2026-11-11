SHELL := /bin/sh
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: install bootstrap-db migrate test lint typecheck check-deploy frontend-install frontend-test frontend-e2e up down

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e 'backend[dev]'

bootstrap-db:
	psql -d postgres -f backend/scripts/bootstrap_roles.sql
	createdb -O inua_migrator inua360 || true

migrate:
	cd backend && DB_USER=$${DB_USER:-inua_app} ../$(PY) manage.py migrate --database=migrator

test:
	cd backend && ../$(PY) -m pytest

lint:
	cd backend && ../$(VENV)/bin/ruff check .
	cd backend && ../$(VENV)/bin/ruff format --check .

typecheck:
	cd backend && ../$(VENV)/bin/mypy apps config

check-deploy:
	cd backend && DJANGO_SETTINGS_MODULE=config.settings.prod \
		DJANGO_SECRET_KEY=$${DJANGO_SECRET_KEY:-ci-only-long-secret-value-1234567890} \
		DJANGO_ALLOWED_HOSTS=localhost \
		../$(PY) manage.py check --deploy

frontend-install:
	cd frontend && npm ci

frontend-test:
	cd frontend && npm run lint && npm run typecheck && npm run test

frontend-e2e:
	cd frontend && npm run e2e

up:
	docker compose up --build

down:
	docker compose down -v
