"""
Etsy & Amazon Mağaza Yönetim Dashboard'u
Çalıştır: streamlit run dashboard.py
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Proje importları - hem lokal hem Streamlit Cloud'da çalışır
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT.parent))

from config.settings import ETSY_DATA_DIR, AMAZON_DATA_DIR
from parsers.etsy_csv import parse_etsy_orders, parse_etsy_listings
from parsers.amazon_csv import parse_amazon_orders, parse_amazon_business_report
from engine.analyzer import (
    build_store_summary,
    get_country_breakdown,
    get_daily_revenue,
    get_top_sellers,
    calculate_period_metrics,
)
from models.order import Order, Platform

# ── Sayfa Ayarları ────────────────────────────────────────
st.set_page_config(
    page_title="Mağaza Yönetim Paneli",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Veri Yükleme (cache'li) ──────────────────────────────
@st.cache_data(ttl=300)
def load_all_data():
    """Tüm CSV dosyalarını yükler ve parse eder."""
    all_orders = []
    all_products = []

    # Etsy
    for f in sorted(ETSY_DATA_DIR.glob("*[Oo]rder*.*sv")):
        all_orders.extend(parse_etsy_orders(f))
    for f in sorted(ETSY_DATA_DIR.glob("*[Ll]isting*.*sv")):
        all_products.extend(parse_etsy_listings(f))

    # Amazon
    for f in sorted(AMAZON_DATA_DIR.glob("*[Oo]rder*.*")):
        all_orders.extend(parse_amazon_orders(f))
    for f in sorted(AMAZON_DATA_DIR.glob("*[Bb]usiness*.*sv")):
        all_products.extend(parse_amazon_business_report(f))

    return all_orders, all_products


def main():
    orders, products = load_all_data()

    if not orders and not products:
        st.error("Veri bulunamadı! Önce `python3 -m ecommerce_manager sample` çalıştırın.")
        return

    # ── Sidebar ───────────────────────────────────────────
    with st.sidebar:
        st.title("📊 Mağaza Paneli")
        st.divider()

        page = st.radio(
            "Sayfa",
            ["Ana Panel", "Ürün Performansı", "Uyarılar & Öneriler"],
            index=0,
        )

        st.divider()

        platform_filter = st.selectbox(
            "Platform",
            ["Tümü", "Etsy", "Amazon"],
        )

        period_days = st.selectbox(
            "Dönem",
            [7, 14, 30, 60, 90],
            index=2,
            format_func=lambda x: f"Son {x} gün",
        )

        st.divider()
        st.caption(f"Toplam {len(orders)} sipariş | {len(products)} ürün")
        if st.button("Verileri Yenile"):
            st.cache_data.clear()
            st.rerun()

    # Platform filtresi uygula
    filtered_orders = orders
    filtered_products = products
    if platform_filter == "Etsy":
        filtered_orders = [o for o in orders if o.platform == Platform.ETSY]
        filtered_products = [p for p in products if p.platform == Platform.ETSY]
    elif platform_filter == "Amazon":
        filtered_orders = [o for o in orders if o.platform == Platform.AMAZON]
        filtered_products = [p for p in products if p.platform == Platform.AMAZON]

    # Sayfa yönlendirme
    if page == "Ana Panel":
        render_main_dashboard(filtered_orders, filtered_products, period_days, platform_filter)
    elif page == "Ürün Performansı":
        render_product_performance(filtered_orders, filtered_products)
    elif page == "Uyarılar & Öneriler":
        render_alerts(filtered_orders, filtered_products, period_days)


# ══════════════════════════════════════════════════════════
#  ANA PANEL
# ══════════════════════════════════════════════════════════
def render_main_dashboard(orders, products, period_days, platform_filter):
    st.title("Ana Panel")
    st.caption(f"Platform: {platform_filter} | Son {period_days} gün")

    today = date.today()
    period_start = today - timedelta(days=period_days)
    prev_start = period_start - timedelta(days=period_days)
    prev_end = period_start - timedelta(days=1)

    current = calculate_period_metrics(orders, period_start, today)
    previous = calculate_period_metrics(orders, prev_start, prev_end)

    # ── KPI Kartları ──────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        delta_orders = None
        if previous.total_orders > 0:
            delta_orders = f"{((current.total_orders - previous.total_orders) / previous.total_orders * 100):+.1f}%"
        st.metric("Sipariş Sayısı", current.total_orders, delta=delta_orders)

    with col2:
        delta_rev = None
        if previous.gross_revenue > 0:
            delta_rev = f"{((current.gross_revenue - previous.gross_revenue) / previous.gross_revenue * 100):+.1f}%"
        st.metric("Brüt Gelir", f"${current.gross_revenue:,.2f}", delta=delta_rev)

    with col3:
        delta_net = None
        if previous.net_revenue > 0:
            delta_net = f"{((current.net_revenue - previous.net_revenue) / previous.net_revenue * 100):+.1f}%"
        st.metric("Net Gelir", f"${current.net_revenue:,.2f}", delta=delta_net)

    with col4:
        st.metric("Ort. Sipariş", f"${current.avg_order_value:,.2f}")

    st.divider()

    # ── Grafikler ─────────────────────────────────────────
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Günlük Satış Trendi")
        daily = get_daily_revenue(orders, days=period_days)
        if daily:
            dates = list(daily.keys())
            revenues = list(daily.values())

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=revenues,
                mode="lines+markers",
                name="Günlük Gelir",
                fill="tozeroy",
                line=dict(color="#4CAF50", width=2),
                marker=dict(size=4),
            ))
            fig.update_layout(
                xaxis_title="Tarih",
                yaxis_title="Gelir ($)",
                height=350,
                margin=dict(l=20, r=20, t=20, b=20),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Ülke Dağılımı")
        countries = get_country_breakdown(orders)
        if countries:
            top_countries = dict(list(countries.items())[:8])
            fig_pie = px.pie(
                names=list(top_countries.keys()),
                values=list(top_countries.values()),
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_pie.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=20, b=20),
                showlegend=True,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # ── Platform Karşılaştırma ────────────────────────────
    etsy_orders = [o for o in orders if o.platform == Platform.ETSY]
    amazon_orders = [o for o in orders if o.platform == Platform.AMAZON]

    if etsy_orders and amazon_orders:
        st.divider()
        st.subheader("Platform Karşılaştırması")

        etsy_rev = sum(o.gross_revenue for o in etsy_orders)
        amazon_rev = sum(o.gross_revenue for o in amazon_orders)

        col_a, col_b = st.columns(2)

        with col_a:
            fig_comp = go.Figure(data=[
                go.Bar(name="Etsy", x=["Sipariş", "Gelir ($)"], y=[len(etsy_orders), etsy_rev], marker_color="#F56400"),
                go.Bar(name="Amazon", x=["Sipariş", "Gelir ($)"], y=[len(amazon_orders), amazon_rev], marker_color="#FF9900"),
            ])
            fig_comp.update_layout(
                barmode="group",
                height=300,
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig_comp, use_container_width=True)

        with col_b:
            # Platform bazlı günlük trend
            etsy_daily = get_daily_revenue(etsy_orders, days=period_days)
            amazon_daily = get_daily_revenue(amazon_orders, days=period_days)

            fig_dual = go.Figure()
            if etsy_daily:
                fig_dual.add_trace(go.Scatter(
                    x=list(etsy_daily.keys()), y=list(etsy_daily.values()),
                    name="Etsy", line=dict(color="#F56400"),
                ))
            if amazon_daily:
                fig_dual.add_trace(go.Scatter(
                    x=list(amazon_daily.keys()), y=list(amazon_daily.values()),
                    name="Amazon", line=dict(color="#FF9900"),
                ))
            fig_dual.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=20, b=20),
                hovermode="x unified",
            )
            st.plotly_chart(fig_dual, use_container_width=True)

    # ── Son Siparişler Tablosu ────────────────────────────
    st.divider()
    st.subheader("Son Siparişler")

    sorted_orders = sorted(orders, key=lambda o: o.order_date, reverse=True)[:20]
    table_data = []
    for o in sorted_orders:
        items_str = ", ".join(item.product_title[:30] for item in o.items[:2])
        table_data.append({
            "Tarih": o.order_date.strftime("%d.%m.%Y"),
            "Platform": o.platform.value.upper(),
            "Sipariş No": o.order_id,
            "Müşteri": o.buyer_name or "-",
            "Ülke": o.buyer_country or "-",
            "Ürünler": items_str,
            "Tutar": f"${o.gross_revenue:,.2f}",
        })

    st.dataframe(table_data, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════
#  ÜRÜN PERFORMANSI
# ══════════════════════════════════════════════════════════
def render_product_performance(orders, products):
    st.title("Ürün Performansı")

    # ── En Çok Satanlar ───────────────────────────────────
    top = get_top_sellers(orders, limit=10)

    if top:
        st.subheader("En Çok Satan Ürünler")

        col_chart, col_table = st.columns([1, 1])

        with col_chart:
            fig = px.bar(
                x=[t.title[:25] for t in top],
                y=[t.revenue for t in top],
                color=[t.units_sold for t in top],
                labels={"x": "Ürün", "y": "Gelir ($)", "color": "Adet"},
                color_continuous_scale="Greens",
            )
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=20, b=80),
                xaxis_tickangle=-45,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            table = []
            for i, t in enumerate(top, 1):
                table.append({
                    "#": i,
                    "Ürün": t.title[:40],
                    "Satış": t.units_sold,
                    "Gelir": f"${t.revenue:,.2f}",
                    "Ort. Fiyat": f"${t.revenue / t.units_sold:,.2f}" if t.units_sold > 0 else "-",
                })
            st.dataframe(table, use_container_width=True, hide_index=True)

    # ── Ürün Detay Tablosu ────────────────────────────────
    if products:
        st.divider()
        st.subheader("Ürün Listesi")

        product_data = []
        for p in products:
            product_data.append({
                "Platform": p.platform.value.upper(),
                "Ürün": p.title[:50],
                "Fiyat": f"${p.price:,.2f}" if p.price > 0 else "-",
                "Stok": p.quantity,
                "Görüntülenme": p.views,
                "Favori": p.favorites,
                "Satış": p.total_sold,
                "Dönüşüm": f"{p.conversion_rate:.1f}%",
                "Durum": p.status,
            })

        st.dataframe(product_data, use_container_width=True, hide_index=True)

        # Dönüşüm oranı grafiği
        st.subheader("Dönüşüm Oranları")
        products_with_views = [p for p in products if p.views > 0]
        if products_with_views:
            fig_conv = px.scatter(
                x=[p.views for p in products_with_views],
                y=[p.conversion_rate for p in products_with_views],
                size=[max(p.total_sold, 1) for p in products_with_views],
                color=[p.platform.value for p in products_with_views],
                hover_name=[p.title[:30] for p in products_with_views],
                labels={"x": "Görüntülenme", "y": "Dönüşüm (%)", "color": "Platform"},
                color_discrete_map={"etsy": "#F56400", "amazon": "#FF9900"},
            )
            fig_conv.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig_conv, use_container_width=True)


# ══════════════════════════════════════════════════════════
#  UYARILAR & ÖNERİLER
# ══════════════════════════════════════════════════════════
def render_alerts(orders, products, period_days):
    st.title("Uyarılar & Öneriler")

    today = date.today()
    period_start = today - timedelta(days=period_days)
    prev_start = period_start - timedelta(days=period_days)
    prev_end = period_start - timedelta(days=1)

    current = calculate_period_metrics(orders, period_start, today)
    previous = calculate_period_metrics(orders, prev_start, prev_end)

    alert_count = 0

    # ── Stok Uyarıları ────────────────────────────────────
    st.subheader("Stok Uyarıları")

    out_of_stock = [p for p in products if p.quantity == 0 and p.status != "sold_out"]
    low_stock = [p for p in products if 0 < p.quantity <= 5]

    if out_of_stock:
        for p in out_of_stock:
            st.error(f"**STOK BİTTİ:** {p.title} ({p.platform.value.upper()}) — Hemen stok ekleyin!")
            alert_count += 1

    if low_stock:
        for p in low_stock:
            st.warning(f"**DÜŞÜK STOK:** {p.title} ({p.platform.value.upper()}) — Kalan: {p.quantity} adet")
            alert_count += 1

    if not out_of_stock and not low_stock:
        st.success("Tüm ürünlerin stoku yeterli.")

    # ── Satış Performans Uyarıları ────────────────────────
    st.divider()
    st.subheader("Performans Uyarıları")

    if previous.gross_revenue > 0:
        change = ((current.gross_revenue - previous.gross_revenue) / previous.gross_revenue) * 100
        if change < -20:
            st.error(f"**GELİR DÜŞÜYOR:** Son {period_days} günde gelir %{abs(change):.0f} azaldı! Fiyat ve listing'leri kontrol edin.")
            alert_count += 1
        elif change < -5:
            st.warning(f"**GELİR UYARISI:** Son {period_days} günde gelir %{abs(change):.0f} azaldı.")
            alert_count += 1
        elif change > 20:
            st.success(f"**HARIKA:** Son {period_days} günde gelir %{change:.0f} arttı!")
        else:
            st.info(f"Gelir değişimi: {change:+.1f}% (önceki döneme göre)")

    if current.total_orders > 0 and current.avg_order_value < 20:
        st.warning(f"**DÜŞÜK SİPARİŞ DEĞERİ:** Ortalama sipariş ${current.avg_order_value:.2f}. Bundle veya upsell stratejisi deneyin.")
        alert_count += 1

    # ── Ürün Bazlı Öneriler ───────────────────────────────
    st.divider()
    st.subheader("Ürün Önerileri")

    # Yüksek görüntülenme ama düşük dönüşüm
    high_view_low_conv = [
        p for p in products
        if p.views > 100 and p.conversion_rate < 1.0
    ]
    if high_view_low_conv:
        for p in high_view_low_conv:
            st.warning(
                f"**DÜŞÜK DÖNÜŞÜM:** {p.title[:40]} — "
                f"{p.views} görüntülenme ama %{p.conversion_rate:.1f} dönüşüm. "
                f"Fiyatı, görselleri veya açıklamayı iyileştirin."
            )
            alert_count += 1

    # Yüksek favori ama düşük satış
    high_fav_low_sale = [
        p for p in products
        if p.favorites > 20 and p.total_sold < 3
    ]
    if high_fav_low_sale:
        for p in high_fav_low_sale:
            st.info(
                f"**FAVORİ AMA SATMIYOR:** {p.title[:40]} — "
                f"{p.favorites} favori ama {p.total_sold} satış. "
                f"Fiyat indirimi veya kampanya deneyin."
            )
            alert_count += 1

    # Hiç satmayan ürünler
    zero_sales = [p for p in products if p.total_sold == 0 and p.views > 50]
    if zero_sales:
        st.divider()
        st.subheader("Hiç Satmayan Ürünler")
        for p in zero_sales:
            st.error(
                f"**SATIŞ YOK:** {p.title[:40]} ({p.platform.value.upper()}) — "
                f"{p.views} görüntülenme, 0 satış. "
                f"Tag'leri, fiyatı ve görselleri gözden geçirin."
            )
            alert_count += 1

    # ── Aksiyon Listesi ───────────────────────────────────
    st.divider()
    st.subheader("Yapılacaklar")

    actions = []
    if out_of_stock:
        actions.append(f"🔴 {len(out_of_stock)} ürüne stok ekle")
    if low_stock:
        actions.append(f"🟡 {len(low_stock)} üründe stok azalıyor, sipariş ver")
    if high_view_low_conv:
        actions.append(f"🟠 {len(high_view_low_conv)} üründe listing optimizasyonu yap")
    if high_fav_low_sale:
        actions.append(f"🔵 {len(high_fav_low_sale)} üründe kampanya düzenle")
    if not actions:
        actions.append("✅ Şu an acil aksiyon gerektiren durum yok")

    for a in actions:
        st.write(f"- {a}")

    # Özet
    st.divider()
    if alert_count == 0:
        st.balloons()
        st.success("Tebrikler! Mağazanızda acil uyarı bulunmuyor.")
    else:
        st.warning(f"Toplam **{alert_count}** uyarı dikkatinizi bekliyor.")


if __name__ == "__main__":
    main()
