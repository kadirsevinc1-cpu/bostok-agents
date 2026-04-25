"""
Güvenlik kontrolü — üretilen HTML/JS kodunda yaygın zafiyetleri tespit eder (0 token).
OWASP Top 10 temel kontrolleri + web sitesi güvenlik en iyi pratikleri.
"""
import re
from dataclasses import dataclass, field


@dataclass
class SecurityReport:
    critical: list[str] = field(default_factory=list)    # Acil düzeltilmeli
    warnings: list[str] = field(default_factory=list)    # Dikkat edilmeli
    passes:   list[str] = field(default_factory=list)    # Güvenli bulunan
    score: int = 100                                       # 100'den başlar, her sorun düşürür

    def summary(self) -> str:
        lines = [f"Güvenlik Skoru: {self.score}/100"]
        if self.critical:
            lines.append(f"KRİTİK ({len(self.critical)}): " + " | ".join(self.critical[:4]))
        if self.warnings:
            lines.append(f"UYARI ({len(self.warnings)}): " + " | ".join(self.warnings[:4]))
        if self.passes:
            lines.append(f"GÜVENLI ({len(self.passes)}): " + ", ".join(self.passes[:5]))
        return "\n".join(lines)


# Hardcoded secret pattern'leri
_SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey|secret|password|passwd|token|auth)\s*[=:]\s*["\']([A-Za-z0-9_\-]{16,})["\']', "Hardcoded secret tespit edildi"),
    (r'sk-[A-Za-z0-9]{32,}',   "OpenAI API key exposed"),
    (r'AIza[A-Za-z0-9_\-]{35}', "Google API key exposed"),
    (r'ghp_[A-Za-z0-9]{36}',   "GitHub token exposed"),
    (r'xox[baprs]-[A-Za-z0-9\-]+', "Slack token exposed"),
]

# XSS risk pattern'leri
_XSS_PATTERNS = [
    (r'innerHTML\s*=\s*(?![\'"]\s*[\'"])', "innerHTML direkt atama (XSS riski)"),
    (r'document\.write\s*\(', "document.write kullanımı (XSS riski)"),
    (r'eval\s*\(', "eval() kullanımı (XSS + injection riski)"),
    (r'setTimeout\s*\(\s*["\']', "setTimeout string ile (XSS riski)"),
    (r'setInterval\s*\(\s*["\']', "setInterval string ile (XSS riski)"),
]

# Tehlikeli inline event handler pattern'leri
_INLINE_EVENT_PATTERNS = [
    (r'on(?:click|load|error|focus|blur|change|submit|mouseover)\s*=\s*["\'].*fetch\s*\(', "Inline event + fetch (XSS riski)"),
    (r'on(?:click|load|error)\s*=\s*["\'].*eval\s*\(', "Inline event + eval (kritik XSS)"),
]

# Açık yönlendirme / tehlikeli link
_REDIRECT_PATTERNS = [
    (r'href\s*=\s*["\']javascript:', "javascript: href kullanımı (XSS)"),
    (r'src\s*=\s*["\']javascript:', "javascript: src (XSS)"),
]


def check_security(html: str) -> SecurityReport:
    rep = SecurityReport()

    # 1. Hardcoded secrets
    for pattern, label in _SECRET_PATTERNS:
        if re.search(pattern, html):
            rep.critical.append(label)
            rep.score -= 25
    if not any(re.search(p, html) for p, _ in _SECRET_PATTERNS):
        rep.passes.append("Hardcoded secret bulunamadı")

    # 2. XSS pattern'leri
    xss_found = []
    for pattern, label in _XSS_PATTERNS:
        if re.search(pattern, html):
            xss_found.append(label)
            rep.score -= 10
    if xss_found:
        rep.critical.extend(xss_found)
    else:
        rep.passes.append("Tehlikeli JS pattern yok")

    # 3. Inline event tehlikeleri
    for pattern, label in _INLINE_EVENT_PATTERNS:
        if re.search(pattern, html, re.IGNORECASE):
            rep.critical.append(label)
            rep.score -= 15

    # 4. javascript: href
    for pattern, label in _REDIRECT_PATTERNS:
        if re.search(pattern, html, re.IGNORECASE):
            rep.critical.append(label)
            rep.score -= 20

    # 5. Harici linkler rel="noopener"
    external_links = re.findall(r'<a[^>]+href=["\']https?://[^"\']+["\'][^>]*>', html, re.IGNORECASE)
    links_without_noopener = [
        l for l in external_links
        if 'target="_blank"' in l.lower() and 'noopener' not in l.lower()
    ]
    if links_without_noopener:
        rep.warnings.append(f"{len(links_without_noopener)} harici link target=_blank ama rel=noopener eksik")
        rep.score -= 5
    elif external_links:
        rep.passes.append("Harici linkler güvenli (noopener var veya _blank yok)")

    # 6. Form action güvenliği
    forms = re.findall(r'<form[^>]*>', html, re.IGNORECASE)
    unsafe_forms = [f for f in forms if 'action=' in f.lower() and 'http://' in f.lower()]
    if unsafe_forms:
        rep.warnings.append(f"{len(unsafe_forms)} form HTTP (HTTPS değil) action'a gönderiyor")
        rep.score -= 10
    elif forms:
        rep.passes.append("Form action'ları güvenli")

    # 7. iFrame sandbox
    iframes = re.findall(r'<iframe[^>]*>', html, re.IGNORECASE)
    unsafe_iframes = [i for i in iframes if 'sandbox' not in i.lower()]
    if unsafe_iframes:
        rep.warnings.append(f"{len(unsafe_iframes)} iframe sandbox attribute'suz")
        rep.score -= 5

    # 8. CSP meta tag
    has_csp = bool(re.search(
        r'<meta[^>]+http-equiv=["\']Content-Security-Policy["\']', html, re.IGNORECASE
    ))
    if has_csp:
        rep.passes.append("CSP meta tag mevcut")
    else:
        rep.warnings.append("CSP meta tag eksik (sunucu header ile eklenebilir)")

    # 9. X-Frame-Options ipucu
    has_xframe = bool(re.search(r'X-Frame-Options', html, re.IGNORECASE))
    if not has_xframe:
        rep.warnings.append("X-Frame-Options header ipucu yok (clickjacking riski — sunucu tarafında ekle)")

    # 10. HTTPS kontrolü — mixed content
    mixed_content = re.findall(r'(?:src|href|action)\s*=\s*["\']http://(?!localhost)', html, re.IGNORECASE)
    if mixed_content:
        rep.warnings.append(f"Mixed content: {len(mixed_content)} HTTP kaynak (HTTPS sayfada güvensiz)")
        rep.score -= 5
    else:
        rep.passes.append("Mixed content yok")

    # 11. Yorum satırlarında bilgi sızıntısı
    comments = re.findall(r'<!--.*?-->', html, re.DOTALL)
    leaked = [c for c in comments if any(
        w in c.lower() for w in ["todo", "password", "secret", "key", "token", "debug", "fix"]
    )]
    if leaked:
        rep.warnings.append(f"{len(leaked)} yorumda hassas kelime (password/secret/key/debug)")
        rep.score -= 5

    # Skor alt sınır
    rep.score = max(rep.score, 0)

    return rep
