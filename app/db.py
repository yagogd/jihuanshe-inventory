"""Database engine and session management (SQLite)."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
engine = create_engine(
    f"sqlite:///{_settings.db_path}",
    echo=False,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.domain import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate() -> None:
    """Lightweight additive migrations for the dev SQLite database.

    ``create_all`` only creates missing tables; it never alters existing ones.
    New columns are added here so a long-lived dev DB keeps up with the models.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "orders" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("orders")}
    additions = {
        "express_company": "VARCHAR",
        "express_tracking": "VARCHAR",
        "shipment_id": "VARCHAR",
    }
    with engine.begin() as conn:
        for name, ddl_type in additions.items():
            if name not in columns:
                conn.execute(text(f"ALTER TABLE orders ADD COLUMN {name} {ddl_type}"))
