"""
ecommerce_manager CLI - Mağaza yönetim sistemi.

Kullanım:
    python -m ecommerce_manager sample     → Örnek veri oluştur
    python -m ecommerce_manager analyze    → Verileri analiz et
    python -m ecommerce_manager report     → Rapor oluştur
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Proje kök dizinini Python path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT.parent))


def cmd_sample(args):
    """Örnek veri oluşturur."""
    from scripts.generate_sample import main as generate
    generate()


def cmd_report(args):
    """Excel satış raporu oluşturur."""
    from datetime import date
    from config.settings import ETSY_DATA_DIR, AMAZON_DATA_DIR, REPORTS_DIR
    from parsers.etsy_csv import parse_etsy_orders, parse_etsy_listings
    from parsers.amazon_csv import parse_amazon_orders, parse_amazon_business_report
    from writers.excel_report import generate_report

    all_orders = []
    all_products = []

    for f in sorted(ETSY_DATA_DIR.glob("*[Oo]rder*.*sv")):
        all_orders.extend(parse_etsy_orders(f))
    for f in sorted(ETSY_DATA_DIR.glob("*[Ll]isting*.*sv")):
        all_products.extend(parse_etsy_listings(f))
    for f in sorted(AMAZON_DATA_DIR.glob("*[Oo]rder*.*")):
        all_orders.extend(parse_amazon_orders(f))
    for f in sorted(AMAZON_DATA_DIR.glob("*[Bb]usiness*.*sv")):
        all_products.extend(parse_amazon_business_report(f))

    if not all_orders:
        print("Veri bulunamadi! Once 'sample' komutu calistirin.")
        return

    output = REPORTS_DIR / f"satis_raporu_{date.today().strftime('%Y%m%d')}.xlsx"
    result = generate_report(
        all_orders, all_products, output,
        period_days=args.days, store_name=args.name,
    )
    print(f"\n  Rapor olusturuldu: {result}")
    print(f"  Siparis sayisi: {len(all_orders)}")
    print(f"  Urun sayisi: {len(all_products)}")


def cmd_optimize(args):
    """Listing SEO analizi ve optimizasyon önerileri."""
    from config.settings import ETSY_DATA_DIR, AMAZON_DATA_DIR
    from parsers.etsy_csv import parse_etsy_listings
    from parsers.amazon_csv import parse_amazon_business_report
    from optimizer.seo_scorer import score_listing
    from optimizer.listing_optimizer import optimize_listing

    all_products = []
    for f in sorted(ETSY_DATA_DIR.glob("*[Ll]isting*.*sv")):
        all_products.extend(parse_etsy_listings(f))
    for f in sorted(AMAZON_DATA_DIR.glob("*[Bb]usiness*.*sv")):
        all_products.extend(parse_amazon_business_report(f))

    if not all_products:
        print("Urun verisi bulunamadi!")
        return

    print(f"\n{'='*60}")
    print(f"  LISTING SEO ANALIZI - {len(all_products)} urun")
    print(f"{'='*60}\n")

    scores = []
    for p in all_products:
        s = score_listing(p)
        scores.append((p, s))

    # Skorlara göre sırala
    scores.sort(key=lambda x: x[1].total_score)

    for p, s in scores:
        print(f"  [{s.grade}] {s.total_score:3d}/100  {p.platform.value.upper():6s}  {p.title[:45]}")
        for issue in s.issues:
            icon = "!!" if issue.severity == "critical" else "!" if issue.severity == "warning" else "i"
            print(f"        [{icon}] {issue.message}")
        print()

    avg = sum(s.total_score for _, s in scores) / len(scores)
    print(f"{'─'*60}")
    print(f"  Ortalama SEO Skoru: {avg:.0f}/100")
    print(f"  Iyi (70+): {sum(1 for _, s in scores if s.total_score >= 70)}")
    print(f"  Zayif (<40): {sum(1 for _, s in scores if s.total_score < 40)}")


def cmd_scrape(args):
    """Etsy/Amazon'da rakip araması yapar."""
    keyword = args.keyword
    platform = args.platform
    pages = args.pages

    print(f"\n  Aranıyor: '{keyword}' | Platform: {platform} | Sayfa: {pages}")
    print(f"  Lutfen bekleyin, bot korumasina takilmamak icin yavas taranıyor...\n")

    if platform in ("etsy", "both"):
        from scraper.etsy_scraper import search_etsy, print_search_report as print_etsy
        report = search_etsy(keyword, max_pages=pages)
        print_etsy(report)

    if platform in ("amazon", "both"):
        from scraper.amazon_scraper import search_amazon, print_search_report as print_amazon
        report = search_amazon(keyword, max_pages=pages)
        print_amazon(report)


def cmd_analyze(args):
    """Mağaza verilerini analiz eder ve özet gösterir."""
    from config.settings import ETSY_DATA_DIR, AMAZON_DATA_DIR
    from parsers.etsy_csv import parse_etsy_orders, parse_etsy_listings
    from parsers.amazon_csv import parse_amazon_orders, parse_amazon_business_report
    from engine.analyzer import build_store_summary, get_country_breakdown, get_daily_revenue
    from models.order import Platform

    all_orders = []
    all_products = []

    # ── Etsy verileri ──
    etsy_order_files = list(ETSY_DATA_DIR.glob("*Order*.*sv")) + list(ETSY_DATA_DIR.glob("*order*.*sv"))
    etsy_listing_files = list(ETSY_DATA_DIR.glob("*Listing*.*sv")) + list(ETSY_DATA_DIR.glob("*listing*.*sv"))

    for f in etsy_order_files:
        print(f"  Etsy siparisler yukleniyor: {f.name}")
        all_orders.extend(parse_etsy_orders(f))

    for f in etsy_listing_files:
        print(f"  Etsy listeler yukleniyor: {f.name}")
        all_products.extend(parse_etsy_listings(f))

    # ── Amazon verileri ──
    amazon_order_files = (
        list(AMAZON_DATA_DIR.glob("*Order*.*")) +
        list(AMAZON_DATA_DIR.glob("*order*.*"))
    )
    amazon_biz_files = (
        list(AMAZON_DATA_DIR.glob("*Business*.*sv")) +
        list(AMAZON_DATA_DIR.glob("*business*.*sv"))
    )

    for f in amazon_order_files:
        print(f"  Amazon siparisler yukleniyor: {f.name}")
        all_orders.extend(parse_amazon_orders(f))

    for f in amazon_biz_files:
        print(f"  Amazon business report yukleniyor: {f.name}")
        all_products.extend(parse_amazon_business_report(f))

    if not all_orders and not all_products:
        print("\n  Veri bulunamadi!")
        print("  Once 'python -m ecommerce_manager sample' ile ornek veri olusturun.")
        print(f"  Veya CSV dosyalarinizi su klasorlere koyun:")
        print(f"    Etsy:   {ETSY_DATA_DIR}")
        print(f"    Amazon: {AMAZON_DATA_DIR}")
        return

    # ── Analiz ──
    print(f"\n{'='*60}")
    print(f"  MAGAZA ANALIZ RAPORU")
    print(f"{'='*60}\n")

    etsy_orders = [o for o in all_orders if o.platform == Platform.ETSY]
    amazon_orders = [o for o in all_orders if o.platform == Platform.AMAZON]

    # Etsy Özet
    if etsy_orders:
        etsy_summary = build_store_summary(
            all_orders, all_products, Platform.ETSY, "Etsy Store"
        )
        _print_summary("ETSY", etsy_summary, etsy_orders)

    # Amazon Özet
    if amazon_orders:
        amazon_summary = build_store_summary(
            all_orders, all_products, Platform.AMAZON, "Amazon Store"
        )
        _print_summary("AMAZON", amazon_summary, amazon_orders)

    # Birleşik
    print(f"\n{'─'*60}")
    print(f"  TOPLAM (Etsy + Amazon)")
    print(f"{'─'*60}")
    print(f"  Toplam Siparis: {len(all_orders)}")
    total_rev = sum(o.gross_revenue for o in all_orders)
    print(f"  Toplam Ciro:    ${total_rev:,.2f}")
    print(f"  Toplam Urun:    {len(all_products)}")

    # Ülke dağılımı
    countries = get_country_breakdown(all_orders)
    print(f"\n  Ulke Dagilimi:")
    for country, count in list(countries.items())[:5]:
        print(f"    {country}: {count} siparis")


def _print_summary(platform_name, summary, orders):
    """Mağaza özetini ekrana yazdırır."""
    print(f"  --- {platform_name} ---")

    cp = summary.current_period
    if cp:
        print(f"  Son 30 Gun:")
        print(f"    Siparis:      {cp.total_orders}")
        print(f"    Brut Gelir:   ${cp.gross_revenue:,.2f}")
        print(f"    Kesintiler:   ${cp.total_fees:,.2f} ({cp.fee_percentage:.1f}%)")
        print(f"    Net Gelir:    ${cp.net_revenue:,.2f}")
        print(f"    Ort. Siparis: ${cp.avg_order_value:,.2f}")

    change = summary.revenue_change
    if change is not None:
        direction = "+" if change >= 0 else ""
        print(f"    Degisim:      {direction}{change:.1f}% (onceki 30 gune gore)")

    if summary.top_sellers:
        print(f"\n  En Cok Satanlar:")
        for i, ts in enumerate(summary.top_sellers[:5], 1):
            print(f"    {i}. {ts.title[:40]:40s} {ts.units_sold:3d} adet  ${ts.revenue:,.2f}")

    if summary.low_stock_products:
        print(f"\n  ⚠ Dusuk Stok:")
        for p in summary.low_stock_products[:5]:
            print(f"    - {p}")

    if summary.out_of_stock_products:
        print(f"\n  ⛔ Stok Bitti:")
        for p in summary.out_of_stock_products[:5]:
            print(f"    - {p}")

    print()


def main():
    parser = argparse.ArgumentParser(
        prog="ecommerce_manager",
        description="Etsy & Amazon Magaza Yonetim Sistemi",
    )
    sub = parser.add_subparsers(dest="command", help="Komutlar")

    sub.add_parser("sample", help="Ornek veri olustur")
    sub.add_parser("analyze", help="Verileri analiz et")
    report_parser = sub.add_parser("report", help="Excel rapor olustur")
    report_parser.add_argument("--days", type=int, default=30, help="Rapor donemi (gun)")
    report_parser.add_argument("--name", type=str, default="Magaza", help="Magaza adi")
    sub.add_parser("optimize", help="Listing SEO analizi ve optimizasyonu")
    scrape_parser = sub.add_parser("scrape", help="Rakip arama ve analizi")
    scrape_parser.add_argument("keyword", help="Aranacak kelime")
    scrape_parser.add_argument("--platform", choices=["etsy", "amazon", "both"], default="both", help="Platform")
    scrape_parser.add_argument("--pages", type=int, default=1, help="Kac sayfa taranacak")

    args = parser.parse_args()

    if args.command == "sample":
        cmd_sample(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "optimize":
        cmd_optimize(args)
    elif args.command == "scrape":
        cmd_scrape(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
