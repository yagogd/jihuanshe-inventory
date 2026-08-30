"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.import_ import router as import_router
from app.api.orders import router as orders_router
from app.config import get_settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


settings = get_settings()
app = FastAPI(title="Jihuanshe Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_router, prefix="/api")
app.include_router(orders_router, prefix="/api")

app.mount("/images", StaticFiles(directory=str(settings.images_dir)), name="images")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
