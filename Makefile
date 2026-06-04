.DEFAULT_GOAL := help
PY ?= python3
PORT ?= 8000

.PHONY: help install demo run test eval eval-live ingest fmt docker docker-up clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime + dev dependencies
	$(PY) -m pip install -r requirements-dev.txt

demo: ## Run the app locally (offline, no keys) -> http://127.0.0.1:8000
	@echo "ParaPilot running at http://127.0.0.1:$(PORT)  (offline stub provider)"
	$(PY) -m uvicorn app.main:app --host 127.0.0.1 --port $(PORT) --reload

run: ## Run the app without auto-reload
	$(PY) -m uvicorn app.main:app --host 127.0.0.1 --port $(PORT)

test: ## Run the test suite (offline)
	PARAPILOT_PROVIDER=stub $(PY) -m pytest -q

eval: ## Run the anti-hallucination eval on the offline stub (grounded vs plain-LLM baseline)
	PARAPILOT_PROVIDER=stub $(PY) -m app.eval.run_eval \
	  --json app/eval/results/latest.json --md app/eval/results/table.md

eval-live: ## Run the SAME eval against a REAL model (needs ANTHROPIC_API_KEY or OPENAI_API_KEY)
	@test -n "$$ANTHROPIC_API_KEY$$OPENAI_API_KEY" || \
	  { echo "Set ANTHROPIC_API_KEY or OPENAI_API_KEY (and optionally PARAPILOT_PROVIDER=openai)"; exit 1; }
	PARAPILOT_PROVIDER=$${PARAPILOT_PROVIDER:-anthropic} $(PY) -m app.eval.run_eval \
	  --json app/eval/results/latest-live.json --md app/eval/results/table-live.md
	@echo "Live results written to app/eval/results/table-live.md — paste them into the README."

ingest: ## Refresh the corpus from live IL sources (writes to data/corpus/_fetched/)
	$(PY) -m app.rag.ingest.run_ingest

docker: ## Build the Docker image
	docker build -t parapilot:latest .

docker-up: ## Run via docker-compose -> http://127.0.0.1:8000
	docker compose up --build

clean: ## Remove caches and the local SQLite DB
	rm -rf .pytest_cache **/__pycache__ *.egg-info parapilot.db
	find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
