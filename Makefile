.PHONY: setup api web test check

setup:
	cd api && uv sync
	cd web && pnpm install

api:
	cd api && uv run uvicorn app.main:app --reload --port 8000

web:
	cd web && pnpm dev

test:
	cd api && uv run pytest -q

check: test
	cd web && pnpm tsc --noEmit && pnpm lint
