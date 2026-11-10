.PHONY: setup api web test check ingest ingest-all seed docker

setup:
	cd api && uv sync
	cd web && pnpm install

api:
	cd api && uv run uvicorn app.main:app --reload --port 8000

web:
	cd web && pnpm dev

# make ingest T=POLYCAB   → one company, everything (filings, prices, fundamentals, transcripts, annual report)
ingest:
	cd api && uv run python -m app.ingest $(T)

# whole portfolio, no document downloads (~1 min)
ingest-all:
	cd api && uv run python -m app.ingest --portfolio --light

test:
	cd api && uv run pytest -q

check: test
	cd api && uvx ruff check app tests
	cd web && pnpm tsc --noEmit && pnpm lint

# rebuild the demo snapshot bundled into the Docker image (personal data stripped)
seed:
	cd api && uv run python scripts/make_seed.py

# build and run the production image locally on :3200
docker:
	docker build -t finn .
	docker run --rm -p 3200:3000 -v finn-data:/data -e FINN_PUBLIC_DEMO=1 --env-file .env finn
