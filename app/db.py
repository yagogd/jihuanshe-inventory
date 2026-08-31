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
    _backfill_cards()
    _seed_cost_categories()
    _remap_legacy_costs()


def _migrate() -> None:
    """Lightweight additive migrations for the dev SQLite database.

    ``create_all`` only creates missing tables; it never alters existing ones.
    New columns are added here (grouped by table) so a long-lived dev DB keeps
    up with the models. Destructive changes are never made; old columns are
    left in place once unused.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)

    def add_columns(table: str, columns: dict[str, str]) -> None:
        if table not in inspector.get_table_names():
            return
        existing = {col["name"] for col in inspector.get_columns(table)}
        with engine.begin() as conn:
            for name, ddl_type in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}"))

    add_columns(
        "orders",
        {
            "express_company": "VARCHAR",
            "express_tracking": "VARCHAR",
            "shipment_id": "VARCHAR",
            "cost_method": "VARCHAR",
            "card_charged_eur_cents": "INTEGER",
        },
    )
    add_columns("order_items", {"card_id": "VARCHAR"})
    add_columns("settings", {"fx_mode": "VARCHAR"})
    add_columns(
        "shipments",
        {
            "total_paid_eur_cents": "INTEGER DEFAULT 0",
            "fx_cny_eur": "FLOAT DEFAULT 0.13",
            "fx_source": "VARCHAR DEFAULT 'fixed'",
        },
    )
    add_columns(
        "shipment_costs",
        {
            "category_id": "VARCHAR",
            "amount": "INTEGER DEFAULT 0",
            "currency": "VARCHAR DEFAULT 'EUR'",
            "insured_amount": "INTEGER",
            "insured_currency": "VARCHAR",
            "position": "INTEGER DEFAULT 0",
        },
    )
    with engine.begin() as conn:
        conn.execute(text("UPDATE orders SET cost_method = 'BY_VALUE' WHERE cost_method IS NULL"))
        conn.execute(text("UPDATE settings SET fx_mode = 'historical' WHERE fx_mode IS NULL"))
        conn.execute(text("UPDATE orders SET fx_source = 'fixed' WHERE fx_source = 'manual'"))
        conn.execute(text("UPDATE shipments SET fx_source = 'fixed' WHERE fx_source IS NULL"))


def _backfill_cards() -> None:
    """Link pre-existing order items to catalog Cards (see domain.cards)."""
    from app.domain.cards import backfill_cards

    with SessionLocal() as session:
        backfill_cards(session)


def _seed_cost_categories() -> None:
    """Insert the default shipping-cost categories when missing."""
    from sqlalchemy import select

    from app.domain import models as m
    from app.domain.enums import CostCategoryKind

    seeds = [
        ("Internacional", CostCategoryKind.SHIPPING),
        ("Seguro", CostCategoryKind.INSURANCE),
        ("Aduanas", CostCategoryKind.CUSTOMS),
        ("Otros", CostCategoryKind.CUSTOM),
    ]
    with SessionLocal() as session:
        existing = {cat.name for cat in session.scalars(select(m.CostCategory))}
        for name, kind in seeds:
            if name not in existing:
                session.add(m.CostCategory(name=name, kind=kind))
        session.commit()


def _remap_legacy_costs() -> None:
    """Remap legacy shipment costs (``type``/``amount_eur_cents``) to categories."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "shipment_costs" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("shipment_costs")}
    if "type" not in columns:
        return  # already migrated / fresh schema

    mapping = {
        "INTERNATIONAL": "Internacional",
        "INSURANCE": "Seguro",
        "CUSTOMS": "Aduanas",
        "OTHER": "Otros",
    }
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT id, type, amount_eur_cents FROM shipment_costs WHERE category_id IS NULL")
        ).fetchall()
        for cost_id, old_type, old_amount in rows:
            category_name = mapping.get(old_type, "Otros")
            category_id = conn.execute(
                text("SELECT id FROM cost_categories WHERE name = :n"), {"n": category_name}
            ).scalar()
            conn.execute(
                text(
                    "UPDATE shipment_costs SET category_id = :c, amount = :a, currency = 'EUR' "
                    "WHERE id = :i"
                ),
                {"c": category_id, "a": old_amount or 0, "i": cost_id},
            )
