.PHONY: install seed api web test check demo

install:
	cd apps/xyz-ai && uv venv --python python3.12 .venv && VIRTUAL_ENV=.venv uv pip install -e ".[dev]"
	cd apps/portal-web && npm install

seed:
	cd apps/xyz-ai && .venv/bin/python -m app.db.seed --reset

api:
	cd apps/xyz-ai && .venv/bin/uvicorn app.main:app --reload --port 8000

web:
	cd apps/portal-web && npm run dev

test:
	cd apps/xyz-ai && .venv/bin/python -m pytest -q

check: test
	cd apps/portal-web && npx tsc --noEmit && npm run build

demo:
	cd apps/xyz-ai && .venv/bin/python -m scripts.demo
