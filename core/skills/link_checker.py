"""
Link Checker Skill — HTML içindeki linkleri ve anchor referanslarını doğrular.
LLM kullanmaz (0 token). Kırık anchor, placeholder link, unresolved template bulur.
"""
import re
from dataclasses import dataclass, field


@dataclass
class LinkReport:
    broken: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if not self.broken and not self.warnings:
            return "✅ Linkler geçerli görünüyor"
        lines = [f"❌ {b}" for b in self.broken[:5]]
        lines += [f"⚠️ {w}" for w in self.warnings[:5]]
        return "\n".join(lines)


def check_links(html: str) -> LinkReport:
    report = LinkReport()

    hrefs = re.findall(r'href=["\']([^"\']{1,200})["\']', html)
    ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', html))

    for href in hrefs:
        if href.startswith("#"):
            anchor = href[1:]
            if anchor and anchor not in ids:
                report.broken.append(f"Anchor bulunamadı: {href}")
        elif href in ("", "javascript:void(0)", "javascript:;", "#"):
            report.warnings.append(f"Boş/sahte link: href='{href}'")
        elif "placeholder" in href.lower() or "example.com" in href.lower():
            report.warnings.append(f"Placeholder link: {href[:60]}")

    # Template / placeholder içerik
    placeholders = re.findall(
        r'\{\{[^}]+\}\}|\[INSERT[^\]]*\]|PLACEHOLDER|Lorem ipsum',
        html, re.IGNORECASE
    )
    for p in set(placeholders[:5]):
        report.warnings.append(f"Doldurulmamış içerik: {p[:40]}")

    # Boş href'li buton/link sayısı
    empty_actions = len(re.findall(r'<(?:button|a)[^>]+href=["\']["\']', html, re.IGNORECASE))
    if empty_actions > 2:
        report.warnings.append(f"{empty_actions} buton/link hedefsiz")

    return report
