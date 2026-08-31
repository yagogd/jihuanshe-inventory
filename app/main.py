"""FastAPI application entrypoint."""
from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import cards, images
from app.api.import_ import router as import_router
from app.api.inventory import router as inventory_router
from app.api.orders import router as orders_router
from app.api.overview import router as overview_router
from app.api.sales import listings_router, sales_router
from app.api.settings import router as settings_router
from app.api.shipments import categories_router
from app.api.shipments import router as shipments_router
from app.config import get_settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if get_settings().auto_translate:
        threading.Thread(target=_background_translate, daemon=True).start()
    yield


def _background_translate() -> None:
    """Fill English names for any cards that still lack them (best effort)."""
    try:
        from app.db import SessionLocal
        from app.domain.translate import translate_all

        with SessionLocal() as db:
            translate_all(db)
    except Exception:
        pass


settings = get_settings()
app = FastAPI(title="Jihuanshe Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_router, prefix="/api")
app.include_router(cards.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(shipments_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
app.include_router(listings_router, prefix="/api")
app.include_router(sales_router, prefix="/api")
app.include_router(overview_router, prefix="/api")

app.mount("/images", StaticFiles(directory=str(settings.images_dir)), name="images")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
