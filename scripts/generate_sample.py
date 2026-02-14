"""
Test için örnek Etsy ve Amazon CSV dosyaları oluşturur.
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ETSY_DIR = PROJECT_ROOT / "data" / "etsy"
AMAZON_DIR = PROJECT_ROOT / "data" / "amazon"

# ── Örnek ürünler ─────────────────────────────────────────

ETSY_PRODUCTS = [
    ("1001", "Handmade Wooden Phone Stand", 24.99, "Home & Living"),
    ("1002", "Custom Name Necklace - Gold", 34.50, "Jewelry"),
    ("1003", "Vintage Style Leather Journal", 29.00, "Paper & Party"),
    ("1004", "Personalized Family Portrait", 45.00, "Art & Collectibles"),
    ("1005", "Macrame Wall Hanging - Large", 55.00, "Home & Living"),
    ("1006", "Ceramic Coffee Mug - Handmade", 18.00, "Home & Living"),
    ("1007", "Digital Wedding Invitation", 12.99, "Paper & Party"),
    ("1008", "Knitted Baby Blanket", 38.00, "Toys & Baby"),
    ("1009", "Resin Earrings - Floral", 15.50, "Jewelry"),
    ("1010", "Custom Pet Portrait Digital", 35.00, "Art & Collectibles"),
]

AMAZON_PRODUCTS = [
    ("B0A1111", "Bamboo Cutting Board Set (3 Pack)", 28.99),
    ("B0A2222", "LED Desk Lamp with USB Charging", 32.50),
    ("B0A3333", "Stainless Steel Water Bottle 750ml", 19.99),
    ("B0A4444", "Organic Cotton Tote Bag - 5 Pack", 22.00),
    ("B0A5555", "Silicone Kitchen Utensil Set", 24.99),
    ("B0A6666", "Yoga Mat with Carrying Strap", 35.00),
    ("B0A7777", "Portable Phone Charger 10000mAh", 27.50),
    ("B0A8888", "Bamboo Toothbrush Set (8 Pack)", 12.99),
    ("B0A9999", "Reusable Beeswax Food Wraps", 16.50),
    ("B0A0000", "Essential Oil Diffuser - Wood Grain", 29.99),
]

COUNTRIES = ["US", "UK", "CA", "AU", "DE", "FR", "TR", "NL", "JP", "IT"]
FIRST_NAMES = ["Emma", "James", "Sarah", "Michael", "Lisa", "David", "Anna", "John", "Maria", "Robert"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Taylor", "Clark"]


def random_date(days_back: int = 90) -> datetime:
    start = datetime.now() - timedelta(days=days_back)
    return start + timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def generate_etsy_orders(count: int = 80) -> None:
    """Etsy sipariş CSV'si oluşturur."""
    ETSY_DIR.mkdir(parents=True, exist_ok=True)
    filepath = ETSY_DIR / "EtsySoldOrders2025.csv"

    headers = [
        "Sale Date", "Order ID", "Buyer User ID", "Full Name",
        "Item Name", "Quantity", "Price", "Coupon Code", "Coupon Details",
        "Discount Amount", "Shipping Discount", "Order Shipping",
        "Order Sales Tax", "Item Total", "Currency", "Transaction ID",
        "Listing ID", "Date Shipped", "Ship City", "Ship State",
        "Ship Zipcode", "Ship Country", "Variations", "Order Type",
        "Tracking Number",
    ]

    rows = []
    for i in range(count):
        product = random.choice(ETSY_PRODUCTS)
        qty = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
        price = product[2]
        total = price * qty
        date = random_date()
        order_id = f"300{1000 + i}"
        discount = round(random.choice([0, 0, 0, total * 0.1, total * 0.15]), 2)
        shipping = round(random.choice([0, 3.99, 5.99, 7.99]), 2)
        tax = round(total * random.choice([0, 0, 0.08, 0.10]), 2)

        rows.append({
            "Sale Date": date.strftime("%b %d, %Y"),
            "Order ID": order_id,
            "Buyer User ID": f"buyer_{random.randint(10000,99999)}",
            "Full Name": random_name(),
            "Item Name": product[1],
            "Quantity": str(qty),
            "Price": f"${price:.2f}",
            "Coupon Code": "",
            "Coupon Details": "",
            "Discount Amount": f"${discount:.2f}",
            "Shipping Discount": "$0.00",
            "Order Shipping": f"${shipping:.2f}",
            "Order Sales Tax": f"${tax:.2f}",
            "Item Total": f"${total:.2f}",
            "Currency": "USD",
            "Transaction ID": f"T{random.randint(100000,999999)}",
            "Listing ID": product[0],
            "Date Shipped": (date + timedelta(days=random.randint(1, 5))).strftime("%b %d, %Y"),
            "Ship City": "Some City",
            "Ship State": "CA",
            "Ship Zipcode": f"{random.randint(10000,99999)}",
            "Ship Country": random.choice(COUNTRIES),
            "Variations": "",
            "Order Type": random.choice(["paid", "completed", "completed", "completed"]),
            "Tracking Number": f"TRK{random.randint(100000000,999999999)}",
        })

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Etsy siparisler: {filepath} ({count} siparis)")


def generate_etsy_listings() -> None:
    """Etsy listing CSV'si oluşturur."""
    ETSY_DIR.mkdir(parents=True, exist_ok=True)
    filepath = ETSY_DIR / "EtsyListingsDownload.csv"

    headers = [
        "TITLE", "DESCRIPTION", "PRICE", "CURRENCY_CODE", "QUANTITY",
        "TAGS", "MATERIALS", "LISTING_ID", "STATE", "URL",
        "VIEWS", "NUM_FAVORERS",
    ]

    rows = []
    for product in ETSY_PRODUCTS:
        tags = ["handmade", "gift", product[3].lower().replace(" & ", ",")]
        views = random.randint(100, 5000)
        favs = int(views * random.uniform(0.02, 0.15))
        qty = random.randint(0, 50)

        rows.append({
            "TITLE": product[1],
            "DESCRIPTION": f"Beautiful {product[1]}. Handmade with love.",
            "PRICE": f"{product[2]:.2f}",
            "CURRENCY_CODE": "USD",
            "QUANTITY": str(qty),
            "TAGS": ",".join(tags),
            "MATERIALS": "mixed",
            "LISTING_ID": product[0],
            "STATE": "active" if qty > 0 else "sold_out",
            "URL": f"https://www.etsy.com/listing/{product[0]}",
            "VIEWS": str(views),
            "NUM_FAVORERS": str(favs),
        })

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Etsy listeler:  {filepath} ({len(rows)} urun)")


def generate_amazon_orders(count: int = 100) -> None:
    """Amazon sipariş raporu oluşturur (tab-separated)."""
    AMAZON_DIR.mkdir(parents=True, exist_ok=True)
    filepath = AMAZON_DIR / "All_Orders_Report.txt"

    headers = [
        "amazon-order-id", "purchase-date", "order-status",
        "product-name", "quantity-purchased", "item-price",
        "item-tax", "shipping-price", "shipping-tax",
        "sku", "asin", "buyer-name", "ship-country",
        "currency", "tracking-number",
    ]

    rows = []
    for i in range(count):
        product = random.choice(AMAZON_PRODUCTS)
        qty = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]
        price = product[2] * qty
        date = random_date()

        rows.append({
            "amazon-order-id": f"111-{random.randint(1000000,9999999)}-{random.randint(1000000,9999999)}",
            "purchase-date": date.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "order-status": random.choice(["Shipped", "Shipped", "Shipped", "Pending", "Cancelled"]),
            "product-name": product[1],
            "quantity-purchased": str(qty),
            "item-price": f"${price:.2f}",
            "item-tax": f"${price * 0.08:.2f}",
            "shipping-price": f"${random.choice([0, 0, 3.99, 5.99]):.2f}",
            "shipping-tax": "$0.00",
            "sku": f"SKU-{product[0][-4:]}",
            "asin": product[0],
            "buyer-name": random_name(),
            "ship-country": random.choices(COUNTRIES, weights=[40, 15, 10, 5, 5, 5, 5, 5, 5, 5])[0],
            "currency": "USD",
            "tracking-number": f"AMZ{random.randint(100000000,999999999)}",
        })

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Amazon siparisler: {filepath} ({count} siparis)")


def generate_amazon_business_report() -> None:
    """Amazon Business Report oluşturur."""
    AMAZON_DIR.mkdir(parents=True, exist_ok=True)
    filepath = AMAZON_DIR / "BusinessReport.csv"

    headers = [
        "(Child) ASIN", "Title", "Sessions", "Session Percentage",
        "Page Views", "Page Views Percentage", "Buy Box Percentage",
        "Units Ordered", "Unit Session Percentage",
        "Ordered Product Sales", "Total Order Items",
    ]

    rows = []
    for product in AMAZON_PRODUCTS:
        sessions = random.randint(50, 2000)
        page_views = int(sessions * random.uniform(1.2, 2.5))
        units = int(sessions * random.uniform(0.02, 0.15))
        revenue = units * product[2]

        rows.append({
            "(Child) ASIN": product[0],
            "Title": product[1],
            "Sessions": str(sessions),
            "Session Percentage": f"{random.uniform(1, 15):.2f}%",
            "Page Views": str(page_views),
            "Page Views Percentage": f"{random.uniform(1, 15):.2f}%",
            "Buy Box Percentage": f"{random.uniform(80, 100):.0f}%",
            "Units Ordered": str(units),
            "Unit Session Percentage": f"{(units/sessions*100):.2f}%",
            "Ordered Product Sales": f"${revenue:.2f}",
            "Total Order Items": str(units),
        })

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Amazon business: {filepath} ({len(rows)} urun)")


def main():
    print("Ornek veri olusturuluyor...\n")
    generate_etsy_orders(80)
    generate_etsy_listings()
    generate_amazon_orders(100)
    generate_amazon_business_report()
    print("\nTamamlandi! 'data/' klasorunu kontrol edin.")


if __name__ == "__main__":
    main()
