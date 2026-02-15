"""
Listing SEO skor hesaplayıcı.
Etsy ve Amazon listinglerini puanlar ve iyileştirme önerileri sunar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from models.order import Platform


@dataclass
class SEOIssue:
    """Tek bir SEO sorunu."""
    category: str        # "title", "tags", "description", "images", "price"
    severity: str        # "critical", "warning", "info"
    message: str
    suggestion: str


@dataclass
class SEOScore:
    """Listing SEO puanı ve detayları."""
    product_id: str
    title: str
    platform: Platform
    total_score: int = 0          # 0-100
    title_score: int = 0          # 0-25
    tags_score: int = 0           # 0-25
    description_score: int = 0    # 0-25
    engagement_score: int = 0     # 0-25
    issues: list[SEOIssue] = field(default_factory=list)
    grade: str = "F"              # A, B, C, D, F

    def calculate_total(self):
        self.total_score = self.title_score + self.tags_score + self.description_score + self.engagement_score
        if self.total_score >= 85:
            self.grade = "A"
        elif self.total_score >= 70:
            self.grade = "B"
        elif self.total_score >= 55:
            self.grade = "C"
        elif self.total_score >= 40:
            self.grade = "D"
        else:
            self.grade = "F"


# ── Etsy SEO Kuralları ────────────────────────────────────

ETSY_TITLE_RULES = {
    "min_length": 40,
    "max_length": 140,
    "min_words": 5,
    "ideal_words": (8, 15),
    "avoid_caps": True,
    "separator_chars": ["-", "|", ",", "~"],
}

ETSY_TAG_RULES = {
    "max_tags": 13,
    "min_tags": 10,
    "max_chars_per_tag": 20,
    "multi_word_preferred": True,
}

# ── Amazon SEO Kuralları ──────────────────────────────────

AMAZON_TITLE_RULES = {
    "min_length": 80,
    "max_length": 200,
    "min_words": 8,
    "ideal_words": (10, 25),
    "include_brand": True,
    "include_size_color": True,
}

# ── Yasaklı / Zayıf Kelimeler ────────────────────────────

WEAK_WORDS = {
    "nice", "good", "great", "beautiful", "amazing", "awesome",
    "best", "perfect", "unique", "special", "cute", "lovely",
    "pretty", "wonderful", "excellent", "fantastic", "gorgeous",
}

POWER_WORDS = {
    "handmade", "custom", "personalized", "organic", "vintage",
    "premium", "luxury", "eco-friendly", "sustainable", "artisan",
    "minimalist", "boho", "rustic", "modern", "gift",
    "wedding", "birthday", "christmas", "mothers day", "fathers day",
}


def score_listing(product, platform: Platform = None) -> SEOScore:
    """
    Bir listing'in SEO puanını hesaplar.

    Args:
        product: Product model nesnesi
        platform: Platform.ETSY veya Platform.AMAZON

    Returns:
        SEOScore nesnesi
    """
    plat = platform or product.platform
    score = SEOScore(
        product_id=product.product_id,
        title=product.title,
        platform=plat,
    )

    _score_title(score, product, plat)
    _score_tags(score, product, plat)
    _score_description(score, product, plat)
    _score_engagement(score, product)
    score.calculate_total()

    return score


def _score_title(score: SEOScore, product, platform: Platform):
    """Başlık puanlaması."""
    title = product.title
    words = title.split()
    points = 25

    if platform == Platform.ETSY:
        rules = ETSY_TITLE_RULES
    else:
        rules = AMAZON_TITLE_RULES

    # Uzunluk kontrolü
    if len(title) < rules["min_length"]:
        points -= 8
        score.issues.append(SEOIssue(
            "title", "critical",
            f"Başlık çok kısa ({len(title)} karakter)",
            f"En az {rules['min_length']} karakter olmalı. Anahtar kelimeler ekleyin.",
        ))
    elif len(title) > rules["max_length"]:
        points -= 5
        score.issues.append(SEOIssue(
            "title", "warning",
            f"Başlık çok uzun ({len(title)} karakter)",
            f"En fazla {rules['max_length']} karakter önerilir.",
        ))

    # Kelime sayısı
    if len(words) < rules["min_words"]:
        points -= 5
        score.issues.append(SEOIssue(
            "title", "warning",
            f"Başlıkta az kelime var ({len(words)})",
            f"En az {rules['min_words']} kelime kullanın.",
        ))
    elif rules["ideal_words"][0] <= len(words) <= rules["ideal_words"][1]:
        points += 0  # ideal, puan kaybı yok

    # Tümü büyük harf kontrolü
    if title.isupper():
        points -= 5
        score.issues.append(SEOIssue(
            "title", "warning",
            "Başlık tamamen büyük harfle yazılmış",
            "İlk harfler büyük, geri kalan küçük harf kullanın.",
        ))

    # Güçlü kelime kontrolü
    title_lower = title.lower()
    has_power = any(pw in title_lower for pw in POWER_WORDS)
    if has_power:
        points = min(points + 3, 25)
    else:
        score.issues.append(SEOIssue(
            "title", "info",
            "Başlıkta güçlü anahtar kelime yok",
            f"Şu kelimelerden eklemeyi deneyin: {', '.join(list(POWER_WORDS)[:5])}",
        ))

    # Zayıf kelime kontrolü
    has_weak = any(ww in title_lower.split() for ww in WEAK_WORDS)
    if has_weak:
        points -= 3
        score.issues.append(SEOIssue(
            "title", "info",
            "Başlıkta zayıf/genel kelimeler var",
            "\"nice\", \"good\", \"beautiful\" gibi genel kelimeleri spesifik kelimelerle değiştirin.",
        ))

    score.title_score = max(0, points)


def _score_tags(score: SEOScore, product, platform: Platform):
    """Tag puanlaması."""
    tags = product.tags if product.tags else []
    points = 25

    if platform == Platform.ETSY:
        rules = ETSY_TAG_RULES

        if len(tags) < rules["min_tags"]:
            points -= 10
            score.issues.append(SEOIssue(
                "tags", "critical",
                f"Yetersiz tag sayısı ({len(tags)}/13)",
                f"Etsy'de 13 tag hakkınız var, en az {rules['min_tags']} kullanın.",
            ))
        elif len(tags) < rules["max_tags"]:
            points -= 3
            score.issues.append(SEOIssue(
                "tags", "warning",
                f"Tag eksik ({len(tags)}/13)",
                "Tüm 13 tag hakkınızı kullanın.",
            ))

        # Çok kelimeli tag kontrolü
        multi_word = sum(1 for t in tags if " " in t)
        if len(tags) > 0 and multi_word / max(len(tags), 1) < 0.5:
            points -= 5
            score.issues.append(SEOIssue(
                "tags", "warning",
                "Çoğu tag tek kelime",
                "Çok kelimeli tag'ler kullanın (örn: 'wooden phone stand' vs 'wooden').",
            ))
    else:
        # Amazon backend keywords farklı çalışır
        if not tags:
            points -= 10
            score.issues.append(SEOIssue(
                "tags", "warning",
                "Backend keyword yok",
                "Amazon backend keywords bölümünü doldurun.",
            ))

    # Tekrar kontrolü
    if len(tags) != len(set(t.lower() for t in tags)):
        points -= 5
        score.issues.append(SEOIssue(
            "tags", "warning",
            "Tekrarlayan tag'ler var",
            "Her tag benzersiz olmalı.",
        ))

    score.tags_score = max(0, points)


def _score_description(score: SEOScore, product, platform: Platform):
    """Açıklama puanlaması."""
    desc = product.description or ""
    points = 25

    if not desc:
        points = 0
        score.issues.append(SEOIssue(
            "description", "critical",
            "Ürün açıklaması yok",
            "Detaylı bir ürün açıklaması yazın (en az 200 karakter).",
        ))
    elif len(desc) < 100:
        points -= 15
        score.issues.append(SEOIssue(
            "description", "critical",
            f"Açıklama çok kısa ({len(desc)} karakter)",
            "En az 200-500 karakter açıklama yazın. Ürün özelliklerini, malzemesini, boyutlarını ekleyin.",
        ))
    elif len(desc) < 300:
        points -= 8
        score.issues.append(SEOIssue(
            "description", "warning",
            f"Açıklama kısa ({len(desc)} karakter)",
            "Daha detaylı açıklama satışı artırır. Kullanım senaryoları, hediye önerileri ekleyin.",
        ))

    # Paragraf/bölüm kontrolü
    if desc and "\n" not in desc and len(desc) > 200:
        points -= 3
        score.issues.append(SEOIssue(
            "description", "info",
            "Açıklama tek paragraf",
            "Başlıklar ve paragraflar ile bölümlere ayırın. Okunabilirliği artırır.",
        ))

    score.description_score = max(0, points)


def _score_engagement(score: SEOScore, product):
    """Etkileşim puanlaması (views, favorites, conversion)."""
    points = 15  # base

    if product.views > 500 and product.conversion_rate > 2.0:
        points = 25
    elif product.views > 200 and product.conversion_rate > 1.0:
        points = 20
    elif product.views > 100:
        points = 15
    elif product.views > 0:
        points = 10
    else:
        points = 5
        score.issues.append(SEOIssue(
            "engagement", "warning",
            "Görüntülenme yok",
            "SEO optimizasyonu yapın, sosyal medyada paylaşın.",
        ))

    if product.views > 200 and product.conversion_rate < 1.0:
        points -= 5
        score.issues.append(SEOIssue(
            "engagement", "warning",
            f"Düşük dönüşüm ({product.conversion_rate:.1f}%)",
            "Çok görüntüleniyor ama satılmıyor. Fiyat, fotoğraf veya açıklamayı iyileştirin.",
        ))

    if product.favorites > 20 and product.total_sold < 3:
        score.issues.append(SEOIssue(
            "engagement", "info",
            f"Yüksek favori ({product.favorites}) ama düşük satış ({product.total_sold})",
            "İndirim veya kampanya ile favori ekleyenleri satışa dönüştürün.",
        ))

    score.engagement_score = max(0, min(25, points))
