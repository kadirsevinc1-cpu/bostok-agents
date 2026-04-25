"""
SEO Checker Skill — meta tag, başlık yapısı, canonical, viewport kontrolü.
LLM kullanmaz (0 token). 0-100 arası puan + sorun listesi döner.
"""
import re
from dataclasses import dataclass, field


@dataclass
class SEOReport:
    score: int = 0
    passed: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def summary(self) -> str:
        stars = "⭐" * (self.score // 20)
        lines = [f"📊 SEO Puanı: {self.score}/100 {stars}"]
        lines += self.passed[:4]
        lines += self.issues[:4]
        return "\n".join(lines)


def check_seo(html: str) -> SEOReport:
    report = SEOReport()
    pts = 0

    # Title
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if m:
        t = m.group(1).strip()
        if 30 <= len(t) <= 60:
            pts += 20
            report.passed.append(f"✅ Title ({len(t)} kar): {t[:40]}")
        else:
            pts += 8
            report.issues.append(f"⚠️ Title uzunluğu ({len(t)} kar, ideal 30-60)")
    else:
        report.issues.append("❌ <title> tag eksik")

    # Meta description
    m = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE
    )
    if not m:
        m = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
            html, re.IGNORECASE
        )
    if m:
        d = m.group(1).strip()
        if 120 <= len(d) <= 160:
            pts += 20
            report.passed.append(f"✅ Meta description ({len(d)} kar)")
        else:
            pts += 8
            report.issues.append(f"⚠️ Meta description ({len(d)} kar, ideal 120-160)")
    else:
        report.issues.append("❌ Meta description eksik")

    # H1
    h1s = re.findall(r"<h1[^>]*>", html, re.IGNORECASE)
    if len(h1s) == 1:
        pts += 15
        report.passed.append("✅ Tek H1 mevcut")
    elif len(h1s) == 0:
        report.issues.append("❌ H1 tag yok")
    else:
        pts += 5
        report.issues.append(f"⚠️ {len(h1s)} adet H1 (sadece 1 olmalı)")

    # Open Graph
    has_og = bool(re.search(r"og:title", html, re.IGNORECASE))
    if has_og:
        pts += 15
        report.passed.append("✅ Open Graph tag'leri mevcut")
    else:
        report.issues.append("⚠️ Open Graph tag'leri eksik")

    # Viewport
    if re.search(r'name=["\']viewport["\']', html, re.IGNORECASE):
        pts += 10
        report.passed.append("✅ Viewport meta tag mevcut")
    else:
        report.issues.append("❌ Viewport meta tag eksik (mobil uyumluluk)")

    # lang attribute
    if re.search(r'<html[^>]+lang=["\']', html, re.IGNORECASE):
        pts += 10
        report.passed.append("✅ HTML lang attribute mevcut")
    else:
        report.issues.append("⚠️ HTML lang attribute eksik")

    # Canonical
    if re.search(r'rel=["\']canonical["\']', html, re.IGNORECASE):
        pts += 10
        report.passed.append("✅ Canonical URL mevcut")
    else:
        report.issues.append("⚠️ Canonical URL eksik")

    report.score = min(pts, 100)
    return report
