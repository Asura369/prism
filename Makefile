SHELL := /bin/bash
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
export FAKE_ADAPTERS ?= 0

.PHONY: setup dev web worker frontend install test test-backend test-frontend demo build clean

setup:
	@test -f assets/fonts/Inter-Regular.ttf && test -f assets/fonts/Inter-Bold.ttf || \
		(echo "SETUP FAILED — missing Inter fonts:"; \
		 echo "  assets/fonts/Inter-Regular.ttf"; \
		 echo "  assets/fonts/Inter-Bold.ttf"; \
		 echo "Get them from https://rsms.me/inter/ (OFL)."; exit 1)
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e 'backend[dev]'
	@if [ -f frontend/package.json ]; then cd frontend && npm install; else echo "frontend/package.json not present yet — skipped npm install"; fi
	@echo "Setup complete. Copy .env.example to .env if you want a real LLM."

dev:
	./scripts/dev.sh

web:
	cd backend && ../$(UVICORN) prism.main:app --reload --port 8000

worker:
	cd backend && ../$(PY) -m prism.worker

frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	cd backend && FAKE_ADAPTERS=1 ../$(VENV)/bin/pytest -x

test-frontend:
	@if [ -d frontend/node_modules ]; then cd frontend && npm run typecheck && npm run test; else echo "frontend deps not installed — skipped"; fi

demo:
	cd backend && FAKE_ADAPTERS=1 ../$(PY) -m prism.demo

build:
	cd frontend && npm run build
	cd backend && ../$(PIP) wheel . -w dist --no-deps

clean:
	rm -rf work/* review/* data/*.db
