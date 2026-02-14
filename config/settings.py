"""
Proje ayarları ve sabit değerler.
"""
from pathlib import Path

# ── Dizinler ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ETSY_DATA_DIR = DATA_DIR / "etsy"
AMAZON_DATA_DIR = DATA_DIR / "amazon"
REPORTS_DIR = PROJECT_ROOT / "reports"

# ── Platform Komisyon Oranları ────────────────────────────
ETSY_COMMISSION = {
    "transaction_fee": 0.065,      # %6.5 işlem ücreti
    "payment_processing": 0.03,    # %3 + $0.25 ödeme işleme
    "payment_fixed": 0.25,         # sabit ödeme ücreti ($)
    "listing_fee": 0.20,           # listing ücreti ($)
    "offsite_ads_fee": 0.15,       # %15 offsite reklam (opsiyonel)
}

AMAZON_COMMISSION = {
    "referral_fee": 0.15,          # %15 referral fee (kategoriye göre değişir)
    "fba_fee_small": 3.22,         # FBA küçük ürün ($)
    "fba_fee_medium": 4.75,        # FBA orta ürün ($)
    "fba_fee_large": 5.80,         # FBA büyük ürün ($)
    "monthly_sub": 39.99,          # Professional plan ($)
}

# ── Para Birimleri ────────────────────────────────────────
CURRENCIES = {
    "USD": "$",
    "EUR": "€",
    "TRY": "₺",
    "GBP": "£",
}

DEFAULT_CURRENCY = "USD"

# ── Rapor Ayarları ────────────────────────────────────────
REPORT_DATE_FORMAT = "%d.%m.%Y"
EXCEL_DATE_FORMAT = "DD.MM.YYYY"
