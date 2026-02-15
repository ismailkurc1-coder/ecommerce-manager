"""
Etsy arama sonuçlarını ve listing detaylarını scrape eder.
Rakip analizi, keyword araştırması ve fiyat karşılaştırması için.
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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


@dataclass
class EtsySearchResult:
    """Etsy arama sonucu."""
    listing_id: str
    title: str
    price: float
    currency: str = "USD"
    shop_name: str = ""
    url: str = ""
    image_url: str = ""
    reviews: int = 0
    rating: float = 0.0
    is_bestseller: bool = False
    is_free_shipping: bool = False
    tags: list[str] = field(default_factory=list)


@dataclass
class EtsySearchReport:
    """Arama raporu."""
    keyword: str
    total_results: int = 0
    results: list[EtsySearchResult] = field(default_factory=list)
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    avg_reviews: float = 0.0
    top_tags: list[str] = field(default_factory=list)


def _get_session() -> requests.Session:
    """Oturum oluşturur."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    })
    # Önce ana sayfayı ziyaret et (cookie almak için)
    try:
        session.get("https://www.etsy.com/", timeout=10)
        time.sleep(1)
    except Exception:
        pass
    return session


def _parse_price(price_str: str) -> float:
    """Fiyat string'ini float'a çevirir."""
    if not price_str:
        return 0.0
    cleaned = re.sub(r'[^\d.,]', '', price_str)
    cleaned = cleaned.replace(',', '')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def search_etsy(keyword: str, max_pages: int = 2, delay: float = 2.0) -> EtsySearchReport:
    """
    Etsy'de arama yapar ve sonuçları döner.

    Args:
        keyword: Aranacak kelime
        max_pages: Kaç sayfa taranacak (her sayfa ~48 sonuç)
        delay: Sayfalar arası bekleme süresi (saniye)

    Returns:
        EtsySearchReport nesnesi
    """
    report = EtsySearchReport(keyword=keyword)
    session = _get_session()
    all_results = []

    for page in range(1, max_pages + 1):
        url = f"https://www.etsy.com/search?q={keyword.replace(' ', '+')}&page={page}"

        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"  Sayfa {page}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Listing kartlarını bul
            listings = soup.select("div.search-listings-group div.js-merch-stash-check-listing")
            if not listings:
                listings = soup.select("li.wt-list-unstyled div[data-listing-id]")
            if not listings:
                # Alternatif selector
                listings = soup.find_all("div", attrs={"data-listing-id": True})

            for item in listings:
                try:
                    result = _parse_listing_card(item)
                    if result:
                        all_results.append(result)
                except Exception:
                    continue

            if page < max_pages:
                time.sleep(delay + random.uniform(0.5, 1.5))

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

        reviews = [r.reviews for r in all_results if r.reviews > 0]
        if reviews:
            report.avg_reviews = sum(reviews) / len(reviews)

        # En sık kullanılan kelimeler (başlıklardan)
        word_count = {}
        stop_words = {"the", "a", "an", "and", "or", "for", "to", "in", "on", "with", "of", "-", "|", ","}
        for r in all_results:
            for word in r.title.lower().split():
                word = word.strip(".,!?()[]{}\"'")
                if word and word not in stop_words and len(word) > 2:
                    word_count[word] = word_count.get(word, 0) + 1

        report.top_tags = [w for w, _ in sorted(word_count.items(), key=lambda x: -x[1])[:20]]

    return report


def _parse_listing_card(item) -> Optional[EtsySearchResult]:
    """Tek bir listing kartını parse eder."""
    listing_id = item.get("data-listing-id", "")

    # Başlık
    title_el = item.select_one("h3") or item.select_one(".v2-listing-card__title")
    title = title_el.get_text(strip=True) if title_el else ""

    if not title:
        return None

    # Fiyat
    price_el = item.select_one("span.currency-value") or item.select_one(".lc-price span")
    price = _parse_price(price_el.get_text(strip=True) if price_el else "0")

    # Mağaza adı
    shop_el = item.select_one("p.shop-name") or item.select_one(".v2-listing-card__shop")
    shop_name = shop_el.get_text(strip=True) if shop_el else ""

    # URL
    link_el = item.select_one("a.listing-link") or item.select_one("a")
    url = link_el.get("href", "") if link_el else ""

    # Görsel
    img_el = item.select_one("img")
    image_url = img_el.get("src", "") if img_el else ""

    # Yorum sayısı
    reviews = 0
    review_el = item.select_one("span.review-count") or item.select_one(".search-review-count")
    if review_el:
        review_text = review_el.get_text(strip=True)
        nums = re.findall(r'[\d,]+', review_text)
        if nums:
            reviews = int(nums[0].replace(',', ''))

    # Bestseller badge
    is_bestseller = bool(item.select_one(".bestseller-badge") or "bestseller" in item.get_text().lower())

    # Free shipping
    is_free_shipping = "free shipping" in item.get_text().lower()

    return EtsySearchResult(
        listing_id=listing_id,
        title=title,
        price=price,
        shop_name=shop_name,
        url=url,
        image_url=image_url,
        reviews=reviews,
        is_bestseller=is_bestseller,
        is_free_shipping=is_free_shipping,
    )


def print_search_report(report: EtsySearchReport):
    """Arama raporunu ekrana yazdırır."""
    print(f"\n{'='*60}")
    print(f"  ETSY ARAMA: '{report.keyword}'")
    print(f"  {report.total_results} sonuc bulundu")
    print(f"{'='*60}\n")

    if report.total_results == 0:
        print("  Sonuc bulunamadi. Etsy bot korumasini aktif etmis olabilir.")
        print("  Birkaç dakika bekleyip tekrar deneyin.")
        return

    print(f"  Fiyat Araligi: ${report.min_price:.2f} - ${report.max_price:.2f}")
    print(f"  Ortalama Fiyat: ${report.avg_price:.2f}")
    print(f"  Ortalama Yorum: {report.avg_reviews:.0f}")

    print(f"\n  En Cok Kullanilan Kelimeler:")
    for i, tag in enumerate(report.top_tags[:10], 1):
        print(f"    {i:2d}. {tag}")

    print(f"\n  --- Ilk 10 Sonuc ---")
    for i, r in enumerate(report.results[:10], 1):
        badge = " [BESTSELLER]" if r.is_bestseller else ""
        ship = " [FREE SHIP]" if r.is_free_shipping else ""
        print(f"  {i:2d}. {r.title[:50]}")
        print(f"      ${r.price:.2f} | {r.reviews} yorum | {r.shop_name}{badge}{ship}")
