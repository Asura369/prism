SHELL := /bin/bash
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
.PHONY: setup dev stop restart web worker frontend install test test-backend test-frontend demo build clean

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
	@echo "Setup complete. Configure a provider in Settings (make dev) to use a real LLM."

dev:
	./scripts/dev.sh

# Bracketed patterns so pkill can't match the shell running it.
stop:
	@pkill -f 'uvicorn prism[.]main:app' || true
	@pkill -f 'prism[.]worker' || true
	@pkill -f 'node_modules/[.]bin/vite' || true
	@sleep 1
	@pgrep -fl 'prism[.]main:app|prism[.]worker|node_modules/[.]bin/vite' \
		|| echo "web, worker, frontend stopped"

restart: stop
	$(MAKE) dev

web:
	cd backend && ../$(UVICORN) prism.main:app --reload --port 8000

worker:
	cd backend && ../$(PY) -m prism.worker

frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	cd backend && ../$(VENV)/bin/pytest -x

test-frontend:
	@if [ -d frontend/node_modules ]; then cd frontend && npm run typecheck && npm run test; else echo "frontend deps not installed — skipped"; fi

demo:
	cd backend && ../$(PY) -m prism.demo

build:
	cd frontend && npm run build
	cd backend && ../$(PIP) wheel . -w dist --no-deps

clean:
	rm -rf work/* review/* data/*.db* frontend/dist
