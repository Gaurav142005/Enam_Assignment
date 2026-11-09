import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import data, network, portfolio, pull, push

app = FastAPI(title="FINN API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FINN_WEB_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (push.router, pull.router, network.router, portfolio.router, data.router):
    app.include_router(r)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
