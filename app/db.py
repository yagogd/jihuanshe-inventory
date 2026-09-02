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
    _repair_card_image_paths()
    _backfill_lots()
    _backfill_lot_sources()
    _consolidate_inventory_lots()
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
            "display_name": "VARCHAR",
        },
    )
    add_columns(
        "order_items",
        {"card_id": "VARCHAR", "excluded_from_inventory": "BOOLEAN DEFAULT 0"},
    )
    add_columns(
        "settings",
        {
            "fx_mode": "VARCHAR",
            "display_currency": "VARCHAR DEFAULT 'EUR'",
            "inventory_page_size": "INTEGER DEFAULT 20",
        },
    )
    add_columns(
        "inventory_lots",
        {
            "card_id": "VARCHAR",
            "source": "VARCHAR DEFAULT 'RECEIVE'",
            "amount": "INTEGER",
            "currency": "VARCHAR",
            "unit_cost_eur_cents": "INTEGER",
            "condition": "VARCHAR",
            "note": "VARCHAR",
            "image_path": "VARCHAR",
        },
    )
    inventory_lot_columns = {
        col["name"]: col for col in inspect(engine).get_columns("inventory_lots")
    }
    if not inventory_lot_columns["order_item_id"].get("nullable", True):
        # Early databases made order_item_id mandatory. Rebuild the SQLite
        # table so manually entered stock can exist without a purchase order.
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE inventory_lots_nullable (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    order_item_id VARCHAR(36),
                    card_id VARCHAR,
                    source VARCHAR DEFAULT 'RECEIVE',
                    quantity INTEGER NOT NULL,
                    available INTEGER NOT NULL,
                    amount INTEGER,
                    currency VARCHAR,
                    unit_cost_eur_cents INTEGER,
                    condition VARCHAR,
                    note VARCHAR,
                    image_path VARCHAR,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY(order_item_id) REFERENCES order_items (id),
                    FOREIGN KEY(card_id) REFERENCES cards (id)
                )
            """))
            conn.execute(text("""
                INSERT INTO inventory_lots_nullable (
                    id, order_item_id, card_id, source, quantity, available,
                    amount, currency, unit_cost_eur_cents, condition, note,
                    image_path, created_at
                )
                SELECT
                    id, order_item_id, card_id, source, quantity, available,
                    amount, currency, unit_cost_eur_cents, condition, note,
                    image_path, created_at
                FROM inventory_lots
            """))
            conn.execute(text("DROP TABLE inventory_lots"))
            conn.execute(text("ALTER TABLE inventory_lots_nullable RENAME TO inventory_lots"))
            conn.execute(text(
                "CREATE INDEX ix_inventory_lots_order_item_id "
                "ON inventory_lots (order_item_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_inventory_lots_card_id ON inventory_lots (card_id)"
            ))
    add_columns("listings", {"marketplace": "VARCHAR DEFAULT 'OTHER'"})
    add_columns("sales", {"bundle_id": "VARCHAR"})
    add_columns("marketplaces", {"enabled": "BOOLEAN DEFAULT 1"})
    add_columns(
        "shipments",
        {
            "display_name": "VARCHAR",
            "total_paid_eur_cents": "INTEGER DEFAULT 0",
            "fx_cny_eur": "FLOAT DEFAULT 0.13",
            "fx_source": "VARCHAR DEFAULT 'fixed'",
            "cost_method": "VARCHAR DEFAULT 'BY_VALUE'",
        },
    )
    add_columns(
        "shipment_costs",
        {
            "category_id": "VARCHAR",
            "type": "VARCHAR DEFAULT 'custom'",
            "amount_eur_cents": "INTEGER DEFAULT 0",
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
        conn.execute(text("UPDATE shipments SET cost_method = 'BY_VALUE' WHERE cost_method IS NULL"))
        conn.execute(
            text(
                "UPDATE order_items SET condition = 'NM' "
                "WHERE condition IS NULL OR condition = '' OR condition = '流通品相'"
            )
        )
        conn.execute(
            text(
                "UPDATE inventory_lots SET condition = 'NM' "
                "WHERE condition IS NULL OR condition = ''"
            )
        )


def _backfill_cards() -> None:
    """Link pre-existing order items to catalog Cards (see domain.cards)."""
    from app.domain.cards import backfill_cards

    with SessionLocal() as session:
        backfill_cards(session)


def _repair_card_image_paths() -> None:
    """Replace stale temporary card paths with an existing order-item image."""
    from sqlalchemy import select

    from app.domain import models as m

    images_dir = get_settings().images_dir
    with SessionLocal() as session:
        cards = list(session.scalars(select(m.Card)))
        changed = False
        for card in cards:
            if card.image_path and (images_dir / card.image_path).is_file():
                continue
            replacement = next(
                (
                    item.image_path
                    for item in card.items
                    if item.image_path and (images_dir / item.image_path).is_file()
                ),
                None,
            )
            if replacement != card.image_path:
                card.image_path = replacement
                changed = True
        if changed:
            session.commit()


def _backfill_lots() -> None:
    """Set ``card_id`` and ``source`` on lots created before the Card model."""
    from sqlalchemy import select

    from app.domain import models as m

    with SessionLocal() as session:
        lots = list(
            session.scalars(
                select(m.InventoryLot).where(m.InventoryLot.card_id.is_(None))
            )
        )
        for lot in lots:
            if lot.order_item is not None and lot.order_item.card_id:
                lot.card_id = lot.order_item.card_id
            if lot.source is None:
                lot.source = m.LotSource.RECEIVE
        session.commit()


def _backfill_lot_sources() -> None:
    """Record the purchase line behind every legacy received inventory lot."""
    from sqlalchemy import select

    from app.domain import models as m

    with SessionLocal() as session:
        known = set(session.scalars(select(m.InventoryLotSource.order_item_id)))
        lots = list(
            session.scalars(
                select(m.InventoryLot).where(m.InventoryLot.order_item_id.is_not(None))
            )
        )
        for lot in lots:
            if lot.order_item_id not in known:
                session.add(m.InventoryLotSource(lot_id=lot.id, order_item_id=lot.order_item_id))
        session.commit()


def _consolidate_inventory_lots() -> None:
    from app.domain.inventory import consolidate_inventory_lots

    with SessionLocal() as session:
        if consolidate_inventory_lots(session):
            session.commit()


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
