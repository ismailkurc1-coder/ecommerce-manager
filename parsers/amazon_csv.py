"""
Amazon CSV/Excel dosyalarını parse eder ve ortak veri modeline dönüştürür.

Amazon Seller Central export formatları:
  - All Orders Report       → Siparişler
  - Business Report          → Sayfa görüntüleme, session, satış
  - Active Listings Report   → Aktif ürünler
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.order import Order, OrderItem, OrderStatus, Platform
from models.product import Product


def _parse_date(date_str: str) -> Optional[datetime]:
    """Amazon tarih formatlarını parse eder."""
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",   # ISO 8601 "2025-01-15T14:30:00+00:00"
        "%Y-%m-%d %H:%M:%S",      # "2025-01-15 14:30:00"
        "%Y-%m-%d",                # "2025-01-15"
        "%m/%d/%Y",                # "01/15/2025"
        "%b %d, %Y",              # "Jan 15, 2025"
        "%d/%m/%Y",                # "15/01/2025"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _parse_money(value: str) -> float:
    """Para değerini float'a çevirir."""
    if not value:
        return 0.0
    cleaned = value.replace("$", "").replace(",", "").replace("€", "").replace("£", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _map_amazon_status(status_str: str) -> OrderStatus:
    """Amazon sipariş durumunu ortak modele eşler."""
    mapping = {
        "pending": OrderStatus.PENDING,
        "unshipped": OrderStatus.PAID,
        "shipped": OrderStatus.SHIPPED,
        "cancelled": OrderStatus.CANCELLED,
        "refunded": OrderStatus.REFUNDED,
    }
    return mapping.get(status_str.lower().strip(), OrderStatus.PENDING)


def parse_amazon_orders(file_path: Path) -> list[Order]:
    """
    Amazon All Orders Report dosyasını parse eder.

    Beklenen sütunlar:
        amazon-order-id, purchase-date, order-status,
        product-name, quantity-purchased, item-price,
        item-tax, shipping-price, shipping-tax,
        sku, asin, buyer-name, ship-country,
        currency, tracking-number
    """
    orders: dict[str, Order] = {}

    # Amazon reports can use tab-separated format
    with open(file_path, "r", encoding="utf-8-sig") as f:
        sample = f.read(1024)
        f.seek(0)
        delimiter = "\t" if "\t" in sample else ","
        reader = csv.DictReader(f, delimiter=delimiter)

        for row in reader:
            order_id = row.get("amazon-order-id", "").strip()
            if not order_id:
                continue

            item = OrderItem(
                product_id=row.get("asin", "").strip(),
                product_title=row.get("product-name", "").strip(),
                quantity=int(row.get("quantity-purchased", "1") or "1"),
                unit_price=_parse_money(row.get("item-price", "0")),
                sku=row.get("sku", "").strip(),
            )

            if order_id in orders:
                orders[order_id].items.append(item)
                orders[order_id].subtotal += _parse_money(row.get("item-price", "0"))
            else:
                order = Order(
                    order_id=order_id,
                    platform=Platform.AMAZON,
                    order_date=_parse_date(row.get("purchase-date", "")) or datetime.now(),
                    status=_map_amazon_status(row.get("order-status", "pending")),
                    items=[item],
                    currency=row.get("currency", "USD").strip(),
                    buyer_name=row.get("buyer-name", "").strip(),
                    buyer_country=row.get("ship-country", "").strip(),
                    subtotal=_parse_money(row.get("item-price", "0")),
                    shipping_cost=_parse_money(row.get("shipping-price", "0")),
                    tax=_parse_money(row.get("item-tax", "0")),
                    tracking_number=row.get("tracking-number", ""),
                    raw_data=dict(row),
                )
                orders[order_id] = order

    return list(orders.values())


def parse_amazon_business_report(file_path: Path) -> list[Product]:
    """
    Amazon Business Report (Detail Page Sales and Traffic) parse eder.

    Beklenen sütunlar:
        (Parent) ASIN, (Child) ASIN, Title, Sessions, Session Percentage,
        Page Views, Page Views Percentage, Buy Box Percentage,
        Units Ordered, Unit Session Percentage, Ordered Product Sales,
        Total Order Items
    """
    products: list[Product] = []

    with open(file_path, "r", encoding="utf-8-sig") as f:
        sample = f.read(1024)
        f.seek(0)
        delimiter = "\t" if "\t" in sample else ","
        reader = csv.DictReader(f, delimiter=delimiter)

        for row in reader:
            asin = row.get("(Child) ASIN", row.get("ASIN", "")).strip()
            if not asin:
                continue

            sessions = int(row.get("Sessions", "0").replace(",", "") or "0")
            page_views = int(row.get("Page Views", "0").replace(",", "") or "0")
            units_ordered = int(row.get("Units Ordered", "0").replace(",", "") or "0")

            product = Product(
                product_id=asin,
                platform=Platform.AMAZON,
                title=row.get("Title", "").strip(),
                price=0.0,  # Business report doesn't include price
                views=page_views,
                total_sold=units_ordered,
                total_revenue=_parse_money(
                    row.get("Ordered Product Sales", "0")
                ),
                raw_data=dict(row),
            )
            products.append(product)

    return products
