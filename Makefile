.PHONY: setup test lint api demo-build demo-docs demo-ingest fault reset datahub-up datahub-down datahub-seed validate eval actions

export PYTHONPATH := $(CURDIR)/src

setup:
	uv sync --extra demo --extra datahub --extra dev

test:
	.venv/bin/python -m pytest

lint:
	.venv/bin/ruff check .

api:
	.venv/bin/uvicorn lineageguard.api:app --reload --host 0.0.0.0 --port 8000

demo-build:
	cd demo/dbt_project && ../../.venv/bin/dbt seed --profiles-dir . && ../../.venv/bin/dbt build --profiles-dir .

demo-docs:
	cd demo/dbt_project && ../../.venv/bin/dbt docs generate --profiles-dir .

demo-ingest:
	.venv/bin/datahub ingest -c infra/recipes/dbt.yml

fault:
	.venv/bin/lineageguard demo inject

reset:
	.venv/bin/lineageguard demo reset

validate:
	.venv/bin/lineageguard demo validate

datahub-seed:
	.venv/bin/lineageguard datahub seed

eval:
	.venv/bin/python evals/run_evals.py --output artifacts/generated/eval-results.json

actions:
	.venv/bin/datahub-actions actions run -c infra/actions/lineageguard.yml

datahub-up:
	mkdir -p .runtime/home
	HOME=$(CURDIR)/.runtime/home DOCKER_HOST=unix://$(HOME)/.docker/run/docker.sock .venv/bin/datahub docker quickstart --version v1.6.0

datahub-down:
	HOME=$(CURDIR)/.runtime/home DOCKER_HOST=unix://$(HOME)/.docker/run/docker.sock .venv/bin/datahub docker quickstart --stop
