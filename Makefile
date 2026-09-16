.PHONY: setup dev-setup up down logs ps test test-backend build-frontend lint clean

setup:
	cp -n .env.example .env || true

dev-setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r backend/requirements-dev.txt

up: setup
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f backend frontend

ps:
	docker compose ps

test: setup test-backend build-frontend

test-backend:
	docker compose build backend
	docker compose run --rm --no-deps backend python -m pytest -q

build-frontend:
	npm --prefix frontend ci
	npm --prefix frontend run build

lint:
	.venv/bin/ruff check backend

clean:
	docker compose down --remove-orphans
