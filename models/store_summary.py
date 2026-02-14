"""
Mağaza özet verileri - Dashboard ve raporlar için.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .order import Platform


@dataclass
class PeriodMetrics:
    """Belirli bir dönem için metrikler."""
    period_start: date
    period_end: date
    total_orders: int = 0
    total_items_sold: int = 0
    gross_revenue: float = 0.0
    total_fees: float = 0.0
    net_revenue: float = 0.0
    shipping_collected: float = 0.0
    refunds: float = 0.0
    avg_order_value: float = 0.0
    unique_buyers: int = 0

    @property
    def fee_percentage(self) -> float:
        if self.gross_revenue == 0:
            return 0.0
        return (self.total_fees / self.gross_revenue) * 100


@dataclass
class ProductPerformance:
    """Ürün performans sıralaması."""
    product_id: str
    title: str
    units_sold: int = 0
    revenue: float = 0.0
    views: int = 0
    conversion_rate: float = 0.0


@dataclass
class StoreSummary:
    """Tek bir mağazanın özet durumu."""
    platform: Platform
    store_name: str
    report_date: date = field(default_factory=date.today)

    # Dönem metrikleri
    current_period: Optional[PeriodMetrics] = None
    previous_period: Optional[PeriodMetrics] = None

    # Ürün performansı
    top_sellers: list[ProductPerformance] = field(default_factory=list)
    low_performers: list[ProductPerformance] = field(default_factory=list)

    # Stok uyarıları
    low_stock_products: list[str] = field(default_factory=list)
    out_of_stock_products: list[str] = field(default_factory=list)

    # Genel istatistikler
    total_active_listings: int = 0
    total_views: int = 0
    overall_conversion_rate: float = 0.0

    @property
    def revenue_change(self) -> Optional[float]:
        """Önceki döneme göre gelir değişimi (%)."""
        if (self.previous_period is None
                or self.current_period is None
                or self.previous_period.gross_revenue == 0):
            return None
        curr = self.current_period.gross_revenue
        prev = self.previous_period.gross_revenue
        return ((curr - prev) / prev) * 100
