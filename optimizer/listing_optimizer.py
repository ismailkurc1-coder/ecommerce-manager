"""
Listing optimizasyonu - kural bazlı + opsiyonel AI.
Başlık, tag, açıklama önerileri üretir.
"""
from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from typing import Optional

from models.order import Platform


@dataclass
class OptimizationResult:
    """Bir ürün için optimizasyon önerileri."""
    product_id: str
    original_title: str
    platform: Platform

    suggested_title: Optional[str] = None
    suggested_tags: list[str] = field(default_factory=list)
    suggested_description: Optional[str] = None
    title_tips: list[str] = field(default_factory=list)
    general_tips: list[str] = field(default_factory=list)
    ai_powered: bool = False


# ── Etsy Kategori Keyword Veritabanı ─────────────────────

ETSY_CATEGORY_KEYWORDS = {
    "jewelry": [
        "handmade jewelry", "minimalist jewelry", "gold jewelry",
        "silver jewelry", "custom jewelry", "personalized jewelry",
        "dainty jewelry", "boho jewelry", "statement jewelry",
        "gift for her", "bridesmaid gift", "wedding jewelry",
        "birthstone jewelry", "name necklace", "initial necklace",
    ],
    "home": [
        "home decor", "wall art", "wall hanging", "farmhouse decor",
        "rustic decor", "modern decor", "minimalist home", "boho decor",
        "housewarming gift", "living room decor", "bedroom decor",
        "shelf decor", "table decor", "handmade decor", "custom sign",
    ],
    "clothing": [
        "handmade clothing", "custom clothing", "vintage style",
        "boho clothing", "minimalist fashion", "sustainable fashion",
        "organic cotton", "linen clothing", "plus size", "unisex",
        "loungewear", "activewear", "streetwear", "casual wear",
    ],
    "art": [
        "wall art", "digital download", "printable art", "custom portrait",
        "pet portrait", "family portrait", "watercolor art", "oil painting",
        "abstract art", "modern art", "minimalist art", "gallery wall",
        "art print", "poster", "illustration",
    ],
    "craft": [
        "craft supplies", "DIY kit", "sewing pattern", "knitting pattern",
        "crochet pattern", "embroidery kit", "beading supplies",
        "jewelry making", "scrapbooking", "sticker", "stamp",
    ],
    "wedding": [
        "wedding gift", "bridal shower", "bridesmaid gift", "groomsmen gift",
        "wedding decor", "wedding invitation", "save the date",
        "wedding favor", "engagement gift", "anniversary gift",
        "wedding sign", "cake topper", "guest book",
    ],
    "baby": [
        "baby gift", "baby shower", "nursery decor", "baby blanket",
        "baby clothes", "personalized baby", "newborn gift",
        "first birthday", "baby milestone", "toddler gift",
    ],
    "digital": [
        "digital download", "printable", "instant download", "PDF",
        "SVG file", "template", "planner", "wall art print",
        "invitation template", "resume template", "social media template",
    ],
}

AMAZON_CATEGORY_KEYWORDS = {
    "kitchen": [
        "kitchen accessories", "cooking utensils", "BPA free",
        "dishwasher safe", "eco friendly", "food grade", "non toxic",
        "set", "pack", "premium quality", "durable", "easy to clean",
    ],
    "home": [
        "home decor", "room decor", "LED", "USB charging",
        "portable", "compact", "modern design", "energy saving",
        "gift idea", "premium", "durable", "easy to use",
    ],
    "fitness": [
        "workout", "exercise", "yoga", "gym", "fitness",
        "non slip", "eco friendly", "portable", "lightweight",
        "carrying strap", "thick", "comfortable", "durable",
    ],
    "electronics": [
        "fast charging", "portable", "compact", "high capacity",
        "lightweight", "USB-C", "LED indicator", "compatible",
        "travel", "backup", "power bank", "wireless",
    ],
    "eco": [
        "eco friendly", "sustainable", "reusable", "organic",
        "biodegradable", "zero waste", "plastic free", "natural",
        "bamboo", "cotton", "recyclable", "green",
    ],
}


def _detect_category(title: str, platform: Platform) -> str:
    """Ürün başlığından kategori tahmin eder."""
    title_lower = title.lower()

    if platform == Platform.ETSY:
        keywords_db = ETSY_CATEGORY_KEYWORDS
    else:
        keywords_db = AMAZON_CATEGORY_KEYWORDS

    best_match = ""
    best_score = 0

    for category, keywords in keywords_db.items():
        match_score = sum(1 for kw in keywords if kw in title_lower)
        # Kategori adı başlıkta geçiyorsa bonus
        if category in title_lower:
            match_score += 3
        if match_score > best_score:
            best_score = match_score
            best_match = category

    return best_match or "home"


def _generate_title_suggestions(product, platform: Platform) -> tuple[str, list[str]]:
    """Kural bazlı başlık optimizasyonu."""
    title = product.title
    tips = []
    words = title.split()

    if platform == Platform.ETSY:
        # Etsy: Anahtar kelime önce, ayırıcılar ile bölümle
        if len(title) < 40:
            tips.append("Başlığı uzatın - en az 60-80 karakter ideal")

        if not any(c in title for c in ["-", "|", ","]):
            tips.append("Ayırıcı kullanın: 'Ürün Adı - Materyal - Kullanım - Hediye Fikri'")

        if title.isupper():
            tips.append("Başlık formatı: Her Kelimenin İlk Harfi Büyük")

        category = _detect_category(title, platform)
        cat_keywords = ETSY_CATEGORY_KEYWORDS.get(category, [])
        unused_keywords = [kw for kw in cat_keywords[:5] if kw.lower() not in title.lower()]
        if unused_keywords:
            tips.append(f"Şu anahtar kelimeleri eklemeyi deneyin: {', '.join(unused_keywords[:3])}")

        # Hediye önerisi
        if "gift" not in title.lower() and "hediye" not in title.lower():
            tips.append("'Gift for Her/Him' veya 'Birthday Gift' gibi hediye kelimeleri ekleyin")

        # Örnek optimized başlık
        parts = [title]
        if unused_keywords:
            parts.append(unused_keywords[0].title())
        if "gift" not in title.lower():
            parts.append("Gift Idea")
        suggested = " | ".join(parts)

    else:
        # Amazon: Brand + Keywords + Size/Color + Quantity
        if len(title) < 80:
            tips.append("Amazon başlığı en az 80 karakter olmalı")

        if len(words) < 8:
            tips.append("Daha fazla anahtar kelime ekleyin")

        category = _detect_category(title, platform)
        cat_keywords = AMAZON_CATEGORY_KEYWORDS.get(category, [])
        unused_keywords = [kw for kw in cat_keywords[:5] if kw.lower() not in title.lower()]
        if unused_keywords:
            tips.append(f"Şu kelimeleri eklemeyi deneyin: {', '.join(unused_keywords[:3])}")

        parts = [title]
        if unused_keywords:
            parts.extend(unused_keywords[:2])
        suggested = " - ".join(parts)

    return suggested[:200], tips


def _generate_tag_suggestions(product, platform: Platform) -> list[str]:
    """Kategori bazlı tag önerileri."""
    existing_tags = set(t.lower() for t in (product.tags or []))
    category = _detect_category(product.title, platform)

    if platform == Platform.ETSY:
        cat_keywords = ETSY_CATEGORY_KEYWORDS.get(category, [])
    else:
        cat_keywords = AMAZON_CATEGORY_KEYWORDS.get(category, [])

    suggested = []
    for kw in cat_keywords:
        if kw.lower() not in existing_tags and len(kw) <= 20:
            suggested.append(kw)
        if len(suggested) + len(existing_tags) >= 13:
            break

    return suggested


def _generate_description_template(product, platform: Platform) -> str:
    """Şablon bazlı açıklama üretici."""
    title = product.title
    category = _detect_category(title, platform)

    if platform == Platform.ETSY:
        template = f"""✨ {title} ✨

🎁 PERFECT GIFT - This {title.lower()} makes a wonderful gift for birthdays, anniversaries, holidays, and special occasions.

📦 WHAT YOU GET:
• 1x {title}
• [Boyut/Ölçü bilgisi ekleyin]
• [Malzeme bilgisi ekleyin]

💎 FEATURES:
• Handmade with care and attention to detail
• [Özellik 1 ekleyin]
• [Özellik 2 ekleyin]
• [Özellik 3 ekleyin]

📐 DIMENSIONS:
• [Genişlik x Yükseklik x Derinlik]
• [Ağırlık]

🚚 SHIPPING:
• Processing time: [X] business days
• Ships from: [Ülke]
• Tracking number provided

⭐ WHY CHOOSE US:
• Handmade quality
• Fast shipping
• Excellent customer service
• Satisfaction guaranteed

💌 Have questions? Send us a message, we'd love to help!

📌 Don't forget to save this to your favorites!"""

    else:
        template = f"""【{title.upper()}】

PRODUCT DESCRIPTION:
{title} - [Ürün açıklaması ekleyin]. Perfect for [kullanım alanı].

KEY FEATURES:
✅ [Özellik 1]
✅ [Özellik 2]
✅ [Özellik 3]
✅ [Özellik 4]
✅ [Özellik 5]

SPECIFICATIONS:
• Material: [Malzeme]
• Size: [Boyut]
• Weight: [Ağırlık]
• Color: [Renk seçenekleri]
• Package Includes: 1x {title}

PERFECT FOR:
🎁 Birthday gifts, holiday gifts, housewarming gifts
👨‍👩‍👧‍👦 Great for the whole family
🏠 [Kullanım alanı 1]
💼 [Kullanım alanı 2]

SATISFACTION GUARANTEE:
We stand behind our products. If you're not 100% satisfied, contact us for a full refund.

Note: [Önemli notlar]"""

    return template


def optimize_listing(product, platform: Platform = None) -> OptimizationResult:
    """
    Kural bazlı listing optimizasyonu yapar.

    Args:
        product: Product model nesnesi
        platform: Platform.ETSY veya Platform.AMAZON

    Returns:
        OptimizationResult nesnesi
    """
    plat = platform or product.platform

    suggested_title, title_tips = _generate_title_suggestions(product, plat)
    suggested_tags = _generate_tag_suggestions(product, plat)
    suggested_desc = _generate_description_template(product, plat)

    general_tips = []

    # Fiyat ipuçları
    if product.price and product.price < 10:
        general_tips.append("Fiyat çok düşük. $15+ fiyat marjı daha iyi kar sağlar.")
    if product.price and product.price % 1 == 0:
        general_tips.append("Psikolojik fiyatlama kullanın: $25.00 yerine $24.99")

    # Stok ipuçları
    if product.quantity <= 5 and product.quantity > 0:
        general_tips.append(f"Stok azalıyor ({product.quantity} adet). Yeniden sipariş verin.")
    if product.quantity == 0:
        general_tips.append("STOK BİTMİŞ! Acil stok ekleyin, listeden düşüyor.")

    # Etkileşim ipuçları
    if product.views > 200 and product.conversion_rate < 1.0:
        general_tips.append("Yüksek trafik ama düşük satış → Fotoğrafları ve fiyatı gözden geçirin.")
    if product.favorites > 10 and product.total_sold == 0:
        general_tips.append("Favorilere ekleniyor ama satılmıyor → İndirim kampanyası deneyin.")
    if product.views < 50:
        general_tips.append("Düşük görüntülenme → SEO'yu iyileştirin, sosyal medyada paylaşın.")

    return OptimizationResult(
        product_id=product.product_id,
        original_title=product.title,
        platform=plat,
        suggested_title=suggested_title,
        suggested_tags=suggested_tags,
        suggested_description=suggested_desc,
        title_tips=title_tips,
        general_tips=general_tips,
        ai_powered=False,
    )


# ── OpenAI Entegrasyonu (Opsiyonel) ──────────────────────

def optimize_listing_ai(product, platform: Platform = None) -> OptimizationResult:
    """
    OpenAI API ile listing optimizasyonu.
    API key yoksa kural bazlı'ya düşer.

    Kullanım:
        export OPENAI_API_KEY="sk-..."
        result = optimize_listing_ai(product)
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return optimize_listing(product, platform)

    plat = platform or product.platform

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)

        platform_name = "Etsy" if plat == Platform.ETSY else "Amazon"

        prompt = f"""You are an expert {platform_name} SEO specialist.

Optimize this product listing:
- Title: {product.title}
- Current Tags: {', '.join(product.tags or [])}
- Price: ${product.price}
- Category hint: {_detect_category(product.title, plat)}

Provide JSON with:
{{
  "optimized_title": "...",
  "tags": ["tag1", "tag2", ...],  // exactly 13 tags for Etsy
  "description": "...",  // full product description
  "tips": ["tip1", "tip2", ...]
}}

Rules for {platform_name}:
- Title should be keyword-rich, {'60-140 chars' if plat == Platform.ETSY else '80-200 chars'}
- Use high-search-volume keywords
- Tags should be multi-word phrases
- Description should be engaging and SEO-optimized
- Include gift-related keywords
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1500,
        )

        data = json.loads(response.choices[0].message.content)

        # Kural bazlı ipuçlarını da ekle
        rule_result = optimize_listing(product, plat)

        return OptimizationResult(
            product_id=product.product_id,
            original_title=product.title,
            platform=plat,
            suggested_title=data.get("optimized_title"),
            suggested_tags=data.get("tags", []),
            suggested_description=data.get("description"),
            title_tips=data.get("tips", []) + rule_result.title_tips,
            general_tips=rule_result.general_tips,
            ai_powered=True,
        )

    except Exception as e:
        print(f"  AI optimizasyon hatasi: {e}")
        print("  Kural bazli optimizasyona geciliyor...")
        return optimize_listing(product, platform)
