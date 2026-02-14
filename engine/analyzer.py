"""
Sipariş ve ürün verilerini analiz eder, özet metrikler üretir.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Optional

from ecommerce_manager.models.order import Order, Platform
from ecommerce_manager.models.product import Product
from ecommerce_manager.models.store_summary import PeriodMetrics, ProductPerformance, StoreSummary


def calculate_period_metrics(
    orders: list[Order],
    start_date: date,
    end_date: date,
) -> PeriodMetrics:
    """Belirli bir dönem için sipariş metriklerini hesaplar."""
    period_orders = [
        o for o in orders
        if start_date <= o.order_date.date() <= end_date
    ]

    buyers = set()
    for o in period_orders:
        if o.buyer_name:
            buyers.add(o.buyer_name)

    total_orders = len(period_orders)
    gross = sum(o.gross_revenue for o in period_orders)
    fees = sum(o.total_fees for o in period_orders)
    net = sum(o.net_revenue for o in period_orders)
    shipping = sum(o.shipping_cost for o in period_orders)
    items = sum(o.item_count for o in period_orders)

    return PeriodMetrics(
        period_start=start_date,
        period_end=end_date,
        total_orders=total_orders,
        total_items_sold=items,
        gross_revenue=gross,
        total_fees=fees,
        net_revenue=net,
        shipping_collected=shipping,
        avg_order_value=gross / total_orders if total_orders > 0 else 0.0,
        unique_buyers=len(buyers),
    )


def get_top_sellers(
    orders: list[Order],
    limit: int = 10,
) -> list[ProductPerformance]:
    """En çok satan ürünleri hesaplar."""
    product_stats: dict[str, dict] = defaultdict(
        lambda: {"title": "", "units": 0, "revenue": 0.0}
    )

    for order in orders:
        for item in order.items:
            pid = item.product_id
            product_stats[pid]["title"] = item.product_title
            product_stats[pid]["units"] += item.quantity
            product_stats[pid]["revenue"] += item.total_price

    sorted_products = sorted(
        product_stats.items(),
        key=lambda x: x[1]["revenue"],
        reverse=True,
    )

    return [
        ProductPerformance(
            product_id=pid,
            title=stats["title"],
            units_sold=stats["units"],
            revenue=stats["revenue"],
        )
        for pid, stats in sorted_products[:limit]
    ]


def get_country_breakdown(orders: list[Order]) -> dict[str, int]:
    """Siparişlerin ülke dağılımını hesaplar."""
    return dict(Counter(
        o.buyer_country for o in orders if o.buyer_country
    ).most_common())


def get_daily_revenue(
    orders: list[Order],
    days: int = 30,
) -> dict[date, float]:
    """Son N gün için günlük gelir."""
    end = date.today()
    start = end - timedelta(days=days)

    daily: dict[date, float] = {}
    current = start
    while current <= end:
        daily[current] = 0.0
        current += timedelta(days=1)

    for order in orders:
        d = order.order_date.date()
        if d in daily:
            daily[d] += order.gross_revenue

    return daily


def build_store_summary(
    orders: list[Order],
    products: list[Product],
    platform: Platform,
    store_name: str,
    period_days: int = 30,
) -> StoreSummary:
    """Mağaza özet raporu oluşturur."""
    today = date.today()

    current_start = today - timedelta(days=period_days)
    previous_start = current_start - timedelta(days=period_days)
    previous_end = current_start - timedelta(days=1)

    platform_orders = [o for o in orders if o.platform == platform]
    platform_products = [p for p in products if p.platform == platform]

    current_metrics = calculate_period_metrics(
        platform_orders, current_start, today
    )
    previous_metrics = calculate_period_metrics(
        platform_orders, previous_start, previous_end
    )

    top = get_top_sellers(platform_orders)

    low_stock = [p.title for p in platform_products if 0 < p.quantity <= 5]
    out_of_stock = [p.title for p in platform_products if p.quantity == 0]
    active = [p for p in platform_products if p.status == "active"]

    total_views = sum(p.views for p in platform_products)
    total_sold = sum(p.total_sold for p in platform_products)

    return StoreSummary(
        platform=platform,
        store_name=store_name,
        current_period=current_metrics,
        previous_period=previous_metrics,
        top_sellers=top,
        low_stock_products=low_stock,
        out_of_stock_products=out_of_stock,
        total_active_listings=len(active),
        total_views=total_views,
        overall_conversion_rate=(
            (total_sold / total_views * 100) if total_views > 0 else 0.0
        ),
    )
