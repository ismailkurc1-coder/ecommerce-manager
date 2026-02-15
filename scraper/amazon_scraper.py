"""
Amazon arama sonuçlarını scrape eder.
Rakip analizi, fiyat karşılaştırması ve keyword araştırması için.
"""
from __future__ import annotations

import re
import time
import random
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


@dataclass
class AmazonSearchResult:
    """Amazon arama sonucu."""
    asin: str
    title: str
    price: float
    currency: str = "USD"
    url: str = ""
    image_url: str = ""
    rating: float = 0.0
    reviews: int = 0
    is_prime: bool = False
    is_bestseller: bool = False
    is_sponsored: bool = False
    brand: str = ""


@dataclass
class AmazonSearchReport:
    """Amazon arama raporu."""
    keyword: str
    total_results: int = 0
    results: list[AmazonSearchResult] = field(default_factory=list)
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    avg_rating: float = 0.0
    avg_reviews: float = 0.0
    prime_percentage: float = 0.0
    top_keywords: list[str] = field(default_factory=list)


def _get_session() -> requests.Session:
    """Oturum oluşturur."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    })
    return session


def _parse_price(price_str: str) -> float:
    """Fiyat parse eder."""
    if not price_str:
        return 0.0
    cleaned = re.sub(r'[^\d.,]', '', price_str)
    cleaned = cleaned.replace(',', '')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def search_amazon(keyword: str, max_pages: int = 2, delay: float = 3.0, domain: str = "com") -> AmazonSearchReport:
    """
    Amazon'da arama yapar.

    Args:
        keyword: Aranacak kelime
        max_pages: Kaç sayfa (her sayfa ~20-48 sonuç)
        delay: Sayfalar arası bekleme (saniye)
        domain: Amazon domain (com, co.uk, de, com.tr vs.)

    Returns:
        AmazonSearchReport nesnesi
    """
    report = AmazonSearchReport(keyword=keyword)
    session = _get_session()
    all_results = []

    for page in range(1, max_pages + 1):
        url = f"https://www.amazon.{domain}/s?k={keyword.replace(' ', '+')}&page={page}"

        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"  Sayfa {page}: HTTP {resp.status_code}")
                if resp.status_code == 503:
                    print("  Amazon bot koruması aktif. Birkaç dakika bekleyin.")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Ürün kartlarını bul
            items = soup.select("div[data-component-type='s-search-result']")

            for item in items:
                try:
                    result = _parse_amazon_card(item, domain)
                    if result and not result.is_sponsored:
                        all_results.append(result)
                except Exception:
                    continue

            if page < max_pages:
                time.sleep(delay + random.uniform(1.0, 2.0))

        except requests.RequestException as e:
            print(f"  Sayfa {page} hata: {e}")
            continue

    # Rapor oluştur
    report.results = all_results
    report.total_results = len(all_results)

    if all_results:
        prices = [r.price for r in all_results if r.price > 0]
        if prices:
            report.avg_price = sum(prices) / len(prices)
            report.min_price = min(prices)
            report.max_price = max(prices)

        ratings = [r.rating for r in all_results if r.rating > 0]
        if ratings:
            report.avg_rating = sum(ratings) / len(ratings)

        reviews = [r.reviews for r in all_results if r.reviews > 0]
        if reviews:
            report.avg_reviews = sum(reviews) / len(reviews)

        prime_count = sum(1 for r in all_results if r.is_prime)
        report.prime_percentage = (prime_count / len(all_results)) * 100

        # Keyword analizi
        word_count = {}
        stop_words = {"the", "a", "an", "and", "or", "for", "to", "in", "on", "with", "of", "-", "|", ",", "&"}
        for r in all_results:
            for word in r.title.lower().split():
                word = word.strip(".,!?()[]{}\"'")
                if word and word not in stop_words and len(word) > 2:
                    word_count[word] = word_count.get(word, 0) + 1

        report.top_keywords = [w for w, _ in sorted(word_count.items(), key=lambda x: -x[1])[:20]]

    return report


def _parse_amazon_card(item, domain: str) -> Optional[AmazonSearchResult]:
    """Tek bir Amazon ürün kartını parse eder."""
    asin = item.get("data-asin", "")
    if not asin:
        return None

    # Sponsored kontrolü
    is_sponsored = bool(item.select_one("span.puis-label-popover-default"))

    # Başlık
    title_el = item.select_one("h2 a span") or item.select_one("h2 span")
    title = title_el.get_text(strip=True) if title_el else ""
    if not title:
        return None

    # URL
    link_el = item.select_one("h2 a")
    url = f"https://www.amazon.{domain}{link_el.get('href', '')}" if link_el else ""

    # Fiyat
    price = 0.0
    price_whole = item.select_one("span.a-price-whole")
    price_frac = item.select_one("span.a-price-fraction")
    if price_whole:
        whole = price_whole.get_text(strip=True).replace(",", "").replace(".", "")
        frac = price_frac.get_text(strip=True) if price_frac else "00"
        try:
            price = float(f"{whole}.{frac}")
        except ValueError:
            price = 0.0

    # Rating
    rating = 0.0
    rating_el = item.select_one("span.a-icon-alt")
    if rating_el:
        rating_match = re.search(r'([\d.]+)', rating_el.get_text())
        if rating_match:
            rating = float(rating_match.group(1))

    # Yorum sayısı
    reviews = 0
    review_el = item.select_one("span.a-size-base.s-underline-text")
    if review_el:
        review_text = review_el.get_text(strip=True).replace(",", "").replace(".", "")
        nums = re.findall(r'\d+', review_text)
        if nums:
            reviews = int(nums[0])

    # Prime
    is_prime = bool(item.select_one("i.a-icon-prime"))

    # Bestseller
    is_bestseller = bool(item.select_one("span.a-badge-text"))

    # Görsel
    img_el = item.select_one("img.s-image")
    image_url = img_el.get("src", "") if img_el else ""

    return AmazonSearchResult(
        asin=asin,
        title=title,
        price=price,
        url=url,
        image_url=image_url,
        rating=rating,
        reviews=reviews,
        is_prime=is_prime,
        is_bestseller=is_bestseller,
        is_sponsored=is_sponsored,
    )


def print_search_report(report: AmazonSearchReport):
    """Amazon arama raporunu yazdırır."""
    print(f"\n{'='*60}")
    print(f"  AMAZON ARAMA: '{report.keyword}'")
    print(f"  {report.total_results} sonuc bulundu")
    print(f"{'='*60}\n")

    if report.total_results == 0:
        print("  Sonuc bulunamadi. Amazon bot korumasini aktif etmis olabilir.")
        print("  Birkaç dakika bekleyip tekrar deneyin.")
        return

    print(f"  Fiyat Araligi: ${report.min_price:.2f} - ${report.max_price:.2f}")
    print(f"  Ortalama Fiyat: ${report.avg_price:.2f}")
    print(f"  Ortalama Rating: {report.avg_rating:.1f}/5")
    print(f"  Ortalama Yorum: {report.avg_reviews:.0f}")
    print(f"  Prime Orani: %{report.prime_percentage:.0f}")

    print(f"\n  En Cok Kullanilan Kelimeler:")
    for i, kw in enumerate(report.top_keywords[:10], 1):
        print(f"    {i:2d}. {kw}")

    print(f"\n  --- Ilk 10 Sonuc ---")
    for i, r in enumerate(report.results[:10], 1):
        badges = []
        if r.is_prime:
            badges.append("PRIME")
        if r.is_bestseller:
            badges.append("BESTSELLER")
        badge_str = f" [{', '.join(badges)}]" if badges else ""

        print(f"  {i:2d}. {r.title[:55]}")
        print(f"      ${r.price:.2f} | {r.rating}/5 ({r.reviews} yorum){badge_str}")
