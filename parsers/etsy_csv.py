"""
Etsy CSV dosyalarını parse eder ve ortak veri modeline dönüştürür.

Etsy export formatları:
  - EtsySoldOrders*.csv  → Satılan siparişler
  - EtsyListings*.csv    → Aktif listeler
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from ecommerce_manager.models.order import Order, OrderItem, OrderStatus, Platform
from ecommerce_manager.models.product import Product


def _parse_date(date_str: str) -> Optional[datetime]:
    """Etsy tarih formatlarını parse eder."""
    formats = [
        "%b %d, %Y",      # "Jan 15, 2025"
        "%m/%d/%Y",        # "01/15/2025"
        "%Y-%m-%d",        # "2025-01-15"
        "%d %b %Y",        # "15 Jan 2025"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _parse_money(value: str) -> float:
    """Para değerini float'a çevirir. '$12.50' → 12.50"""
    if not value:
        return 0.0
    cleaned = value.replace("$", "").replace(",", "").replace("€", "").replace("£", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _map_etsy_status(status_str: str) -> OrderStatus:
    """Etsy sipariş durumunu ortak modele eşler."""
    mapping = {
        "paid": OrderStatus.PAID,
        "completed": OrderStatus.DELIVERED,
        "shipped": OrderStatus.SHIPPED,
        "cancelled": OrderStatus.CANCELLED,
        "refunded": OrderStatus.REFUNDED,
        "open": OrderStatus.PENDING,
    }
    return mapping.get(status_str.lower().strip(), OrderStatus.PENDING)


def parse_etsy_orders(file_path: Path) -> list[Order]:
    """
    Etsy sipariş CSV dosyasını parse eder.

    Beklenen sütunlar (Etsy standart export):
        Sale Date, Order ID, Buyer User ID, Full Name,
        Item Name, Quantity, Price, Coupon Code, Coupon Details,
        Discount Amount, Shipping Discount, Order Shipping,
        Order Sales Tax, Item Total, Currency, Transaction ID,
        Listing ID, Date Shipped, Street 1, Street 2, Ship City,
        Ship State, Ship Zipcode, Ship Country, Order Type
    """
    orders: dict[str, Order] = {}

    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            order_id = row.get("Order ID", "").strip()
            if not order_id:
                continue

            item = OrderItem(
                product_id=row.get("Listing ID", "").strip(),
                product_title=row.get("Item Name", "").strip(),
                quantity=int(row.get("Quantity", "1") or "1"),
                unit_price=_parse_money(row.get("Price", "0")),
                variation=row.get("Variations", ""),
            )

            if order_id in orders:
                orders[order_id].items.append(item)
                orders[order_id].subtotal += _parse_money(row.get("Item Total", "0"))
            else:
                order = Order(
                    order_id=order_id,
                    platform=Platform.ETSY,
                    order_date=_parse_date(row.get("Sale Date", "")) or datetime.now(),
                    status=_map_etsy_status(row.get("Order Type", "paid")),
                    items=[item],
                    currency=row.get("Currency", "USD").strip(),
                    buyer_name=row.get("Full Name", "").strip(),
                    buyer_country=row.get("Ship Country", "").strip(),
                    subtotal=_parse_money(row.get("Item Total", "0")),
                    shipping_cost=_parse_money(row.get("Order Shipping", "0")),
                    tax=_parse_money(row.get("Order Sales Tax", "0")),
                    discount=_parse_money(row.get("Discount Amount", "0")),
                    tracking_number=row.get("Tracking Number", ""),
                    raw_data=dict(row),
                )
                orders[order_id] = order

    return list(orders.values())


def parse_etsy_listings(file_path: Path) -> list[Product]:
    """
    Etsy listing CSV dosyasını parse eder.

    Beklenen sütunlar:
        TITLE, DESCRIPTION, PRICE, CURRENCY_CODE, QUANTITY,
        TAGS, MATERIALS, LISTING_ID, STATE, URL, VIEWS, NUM_FAVORERS
    """
    products: list[Product] = []

    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            tags_raw = row.get("TAGS", "")
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

            status_map = {
                "active": "active",
                "inactive": "inactive",
                "draft": "draft",
                "sold_out": "sold_out",
            }

            product = Product(
                product_id=row.get("LISTING_ID", "").strip(),
                platform=Platform.ETSY,
                title=row.get("TITLE", "").strip(),
                price=_parse_money(row.get("PRICE", "0")),
                currency=row.get("CURRENCY_CODE", "USD").strip(),
                description=row.get("DESCRIPTION", "").strip(),
                tags=tags,
                status=status_map.get(
                    row.get("STATE", "active").lower().strip(), "active"
                ),
                quantity=int(row.get("QUANTITY", "0") or "0"),
                views=int(row.get("VIEWS", "0") or "0"),
                favorites=int(row.get("NUM_FAVORERS", "0") or "0"),
                raw_data=dict(row),
            )
            products.append(product)

    return products
