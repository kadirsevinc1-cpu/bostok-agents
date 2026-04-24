"""SEO Analizci — web sitesini scrape eder, 0-100 puan verir, sorunları listeler."""
import asyncio
import re
import time
from dataclasses import dataclass, field
from loguru import logger

import aiohttp

VIEWPORT_RE    = re.compile(r'<meta[^>]+name=["\']viewport["\']', re.I)
TITLE_RE       = re.compile(r'<title[^>]*>(.*?)</title>', re.I | re.S)
META_DESC_RE   = re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']', re.I)
CONTACT_RE     = re.compile(r'href=["\'][^"\']*(?:contact|iletisim|kontakt|impressum|about|hakkimizda)[^"\']*["\']', re.I)
SOCIAL_RE      = re.compile(r'href=["\'][^"\']*(?:facebook\.com|instagram\.com|twitter\.com|linkedin\.com|youtube\.com)[^"\']*["\']', re.I)


@dataclass
class SEOReport:
    url: str
    score: int = 0
    response_time: float = 0.0
    has_https: bool = False
    has_viewport: bool = False
    has_title: bool = False
    title: str = ""
    has_meta_description: bool = False
    has_contact_page: bool = False
    has_social_links: bool = False
    error: str = ""
    issues: list[str] = field(default_factory=list)
    positives: list[str] = field(default_factory=list)

    def telegram_summary(self) -> str:
        emoji = "🟢" if self.score >= 70 else ("🟡" if self.score >= 40 else "🔴")
        lines = [f"📊 <b>SEO Analizi</b>\n{self.url}\n{emoji} Puan: <b>{self.score}/100</b>"]
        if self.response_time > 0:
            sp = "🐢" if self.response_time > 3.5 else ("⚠️" if self.response_time > 1.5 else "⚡")
            lines.append(f"{sp} Yanıt: {self.response_time:.1f} sn")
        lines.append("")
        for p in self.positives:
            lines.append(f"✅ {p}")
        for i in self.issues:
            lines.append(f"❌ {i}")
        if self.error:
            lines.append(f"\n⚠️ Hata: {self.error}")
        return "\n".join(lines)

    def for_email_prompt(self) -> str:
        """Email yazımı için kısa sorun özeti."""
        if not self.issues:
            return ""
        return "Mevcut site sorunları: " + "; ".join(self.issues[:4])


async def analyze(url: str) -> SEOReport:
    if not url.startswith("http"):
        url = "https://" + url

    report = SEOReport(url=url)
    report.has_https = url.startswith("https://")
    if report.has_https:
        report.positives.append("HTTPS (güvenli)")
    else:
        report.issues.append("HTTPS yok")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        start = time.monotonic()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
                allow_redirects=True,
            ) as resp:
                report.response_time = time.monotonic() - start
                html = await resp.text(errors="ignore")

        if report.response_time > 3.5:
            report.issues.append(f"Çok yavaş ({report.response_time:.1f} sn)")
        elif report.response_time > 1.5:
            report.issues.append(f"Yavaş ({report.response_time:.1f} sn)")
        else:
            report.positives.append(f"Hızlı ({report.response_time:.1f} sn)")

        report.has_viewport = bool(VIEWPORT_RE.search(html))
        if report.has_viewport:
            report.positives.append("Mobil uyumlu")
        else:
            report.issues.append("Mobil uyumsuz")

        title_m = TITLE_RE.search(html)
        if title_m:
            report.has_title = True
            report.title = title_m.group(1).strip()[:60]
            report.positives.append("Title mevcut")
        else:
            report.issues.append("Title eksik")

        report.has_meta_description = bool(META_DESC_RE.search(html))
        if report.has_meta_description:
            report.positives.append("Meta description mevcut")
        else:
            report.issues.append("Meta description eksik")

        report.has_contact_page = bool(CONTACT_RE.search(html))
        if report.has_contact_page:
            report.positives.append("İletişim sayfası var")
        else:
            report.issues.append("İletişim sayfası yok")

        report.has_social_links = bool(SOCIAL_RE.search(html))
        if report.has_social_links:
            report.positives.append("Sosyal medya bağlantısı var")
        else:
            report.issues.append("Sosyal medya bağlantısı yok")

    except aiohttp.ClientSSLError:
        report.issues.append("SSL sertifikası geçersiz")
        report.error = "SSL hatası"
    except asyncio.TimeoutError:
        report.issues.append("Site yanıt vermiyor")
        report.error = "Timeout"
    except Exception as e:
        report.error = str(e)[:80]
        logger.debug(f"SEO analiz hata [{url}]: {e}")

    weights = {
        "has_https": 20, "has_viewport": 20,
        "has_title": 15, "has_meta_description": 15,
        "has_contact_page": 10, "has_social_links": 5,
    }
    speed_score = 15 if report.response_time < 1.5 else (7 if report.response_time < 3.5 else 0)
    report.score = sum(v for k, v in weights.items() if getattr(report, k, False)) + speed_score

    logger.info(f"SEO analiz: {url} → {report.score}/100 ({len(report.issues)} sorun)")
    return report
