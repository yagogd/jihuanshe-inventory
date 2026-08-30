from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.domain.enums import ShipmentStatus
from app.domain.models import InventoryLot, Order, OrderItem, Sale, Shipment
from app.domain.overview import compute_overview


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_overview_sales_and_invested():
    db = _session()
    order = Order(seller="s", total_paid_fen=1000, fx_cny_eur=0.13)
    order.items.append(
        OrderItem(raw_name="Carta", normalized_name="Carta", quantity=1, unit_price_fen=1000)
    )
    db.add(order)
    db.flush()

    shipment = Shipment(status=ShipmentStatus.PREPARING)
    shipment.orders.append(order)
    db.add(shipment)
    db.flush()

    lot = InventoryLot(order_item_id=order.items[0].id, quantity=1, available=0)
    db.add(lot)
    db.flush()
    db.add(
        Sale(
            lot_id=lot.id,
            quantity=1,
            unit_price_eur_cents=200,
            fees_eur_cents=10,
            landed_unit_eur_cents=130,
        )
    )
    db.commit()

    overview = compute_overview(db)
    assert overview["orders_count"] == 1
    assert overview["invested_eur_cents"] == 130
    assert overview["sold_units"] == 1
    assert overview["revenue_eur_cents"] == 200
    assert overview["cost_eur_cents"] == 140
    assert overview["profit_eur_cents"] == 60
    assert overview["roi_pct"] == 42.9
    assert overview["inventory_units"] == 0
    assert overview["inventory_value_eur_cents"] == 0


def test_overview_inventory_value():
    db = _session()
    order = Order(total_paid_fen=2000, fx_cny_eur=0.13)
    order.items.append(
        OrderItem(raw_name="Carta", normalized_name="Carta", quantity=2, unit_price_fen=1000)
    )
    db.add(order)
    db.flush()
    db.add(InventoryLot(order_item_id=order.items[0].id, quantity=2, available=2))
    db.commit()

    overview = compute_overview(db)
    assert overview["inventory_units"] == 2
    assert overview["inventory_value_eur_cents"] == 260
