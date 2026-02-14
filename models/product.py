"""
Ürün veri modeli - Etsy ve Amazon ürünleri bu ortak modele dönüşür.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from models.order import Platform


class ProductStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    SOLD_OUT = "sold_out"


@dataclass
class Product:
    """Platform-bağımsız ürün modeli."""
    product_id: str
    platform: Platform
    title: str
    price: float
    currency: str = "USD"

    # Detaylar
    sku: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    status: str = ProductStatus.ACTIVE

    # Stok
    quantity: int = 0

    # Performans metrikleri
    views: int = 0
    favorites: int = 0
    total_sold: int = 0
    total_revenue: float = 0.0

    # Tarihler
    created_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None

    # Maliyet (kar hesabı için)
    cost_price: Optional[float] = None
    shipping_cost_estimate: Optional[float] = None

    # Ham veri referansı
    raw_data: dict = field(default_factory=dict, repr=False)

    @property
    def conversion_rate(self) -> float:
        """Görüntülenme → satış dönüşüm oranı (%)."""
        if self.views == 0:
            return 0.0
        return (self.total_sold / self.views) * 100

    @property
    def favorite_rate(self) -> float:
        """Görüntülenme → favori oranı (%)."""
        if self.views == 0:
            return 0.0
        return (self.favorites / self.views) * 100

    @property
    def profit_margin(self) -> Optional[float]:
        """Kar marjı (%) - maliyet girilmişse."""
        if self.cost_price is None or self.price == 0:
            return None
        return ((self.price - self.cost_price) / self.price) * 100
