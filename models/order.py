"""
Sipariş veri modeli - Etsy ve Amazon siparişleri bu ortak modele dönüşür.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    ETSY = "etsy"
    AMAZON = "amazon"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass
class OrderItem:
    """Siparişteki tek bir ürün kalemi."""
    product_id: str
    product_title: str
    quantity: int
    unit_price: float
    sku: Optional[str] = None
    variation: Optional[str] = None

    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class Order:
    """Platform-bağımsız sipariş modeli."""
    order_id: str
    platform: Platform
    order_date: datetime
    status: OrderStatus
    items: list[OrderItem] = field(default_factory=list)
    currency: str = "USD"

    # Müşteri bilgileri
    buyer_name: Optional[str] = None
    buyer_country: Optional[str] = None

    # Finansal
    subtotal: float = 0.0
    shipping_cost: float = 0.0
    tax: float = 0.0
    discount: float = 0.0
    platform_fee: float = 0.0
    payment_processing_fee: float = 0.0

    # Kargo
    tracking_number: Optional[str] = None
    shipping_method: Optional[str] = None

    # Ham veri referansı
    raw_data: dict = field(default_factory=dict, repr=False)

    @property
    def gross_revenue(self) -> float:
        """Brüt gelir (ürün + kargo)."""
        return self.subtotal + self.shipping_cost

    @property
    def total_fees(self) -> float:
        """Toplam platform kesintileri."""
        return self.platform_fee + self.payment_processing_fee

    @property
    def net_revenue(self) -> float:
        """Net gelir (kesintiler sonrası)."""
        return self.gross_revenue - self.total_fees - self.tax + self.discount

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)
