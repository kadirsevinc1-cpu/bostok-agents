"""Erişilebilirlik kontrolü — WCAG 2.1 temel kontroller, 0 token."""
import re
from dataclasses import dataclass, field


@dataclass
class AccessibilityReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = []
        if self.errors:
            lines.append(f"HATA ({len(self.errors)}): " + " | ".join(self.errors[:5]))
        if self.warnings:
            lines.append(f"UYARI ({len(self.warnings)}): " + " | ".join(self.warnings[:5]))
        if self.passes:
            lines.append(f"GECTI ({len(self.passes)}): " + ", ".join(self.passes[:5]))
        return "\n".join(lines) or "Erisebilirlik analizi tamamlandi."


def check_accessibility(html: str) -> AccessibilityReport:
    rep = AccessibilityReport()

    # 1. Resimler — alt etiketi
    imgs = re.findall(r"<img[^>]*>", html, re.IGNORECASE)
    imgs_no_alt = [img for img in imgs if "alt=" not in img.lower()]
    if imgs_no_alt:
        rep.errors.append(f"{len(imgs_no_alt)} resimde alt etiketi eksik")
    elif imgs:
        rep.passes.append("Tum resimlerde alt etiketi var")

    # 2. Bos button
    empty_btns = re.findall(r"<button[^>]*>\s*</button>", html, re.IGNORECASE)
    if empty_btns:
        rep.errors.append(f"{len(empty_btns)} bos button (icerik/aria-label yok)")
    else:
        rep.passes.append("Buttonlar icerik iceriyor")

    # 3. Bos link
    empty_links = re.findall(r"<a[^>]*>\s*</a>", html, re.IGNORECASE)
    if empty_links:
        rep.warnings.append(f"{len(empty_links)} bos anchor etiketi")

    # 4. Form label eslesmesi
    inputs = re.findall(
        r'<input[^>]*type=["\'](?!hidden)[^"\']*["\'][^>]*>', html, re.IGNORECASE
    )
    labels = re.findall(r"<label[^>]*>", html, re.IGNORECASE)
    if inputs and len(labels) < len(inputs):
        rep.warnings.append(
            f"Input ({len(inputs)}) > label ({len(labels)}) — bazi inputlar etiketsiz"
        )
    elif inputs:
        rep.passes.append("Form inputlari etiketli")

    # 5. ARIA landmarks
    if re.search(r"<main[\s>]|role=[\"']main[\"']", html, re.IGNORECASE):
        rep.passes.append("<main> landmark var")
    else:
        rep.warnings.append("<main> landmark eksik")

    if re.search(r"<nav[\s>]|role=[\"']navigation[\"']", html, re.IGNORECASE):
        rep.passes.append("<nav> landmark var")
    else:
        rep.warnings.append("<nav> landmark eksik")

    # 6. HTML lang attribute
    if re.search(r"<html[^>]*lang=", html, re.IGNORECASE):
        rep.passes.append("HTML lang attribute var")
    else:
        rep.errors.append("HTML lang attribute eksik (erisebilirlik zorunlu)")

    # 7. Skip to content
    if re.search(r"skip.*content|atla.*icerik|icerige.*atla", html, re.IGNORECASE):
        rep.passes.append("Skip-to-content linki var")
    else:
        rep.warnings.append("Skip-to-content linki onerilir (klavye kullananlar icin)")

    # 8. tabindex misuse
    bad_tab = re.findall(r'tabindex=["\'][1-9]\d*["\']', html)
    if bad_tab:
        rep.warnings.append(
            f"tabindex > 0 kullanimi ({len(bad_tab)} yerde) — tab sirasi bozulabilir"
        )

    # 9. aria-label / aria-labelledby varligı
    aria_count = len(re.findall(r"aria-(?:label|labelledby|describedby)=", html, re.IGNORECASE))
    if aria_count > 0:
        rep.passes.append(f"{aria_count} yerde ARIA etiket var")
    else:
        rep.warnings.append("Hic ARIA etiket bulunamadi")

    # 10. role attribute kullanimi
    roles = re.findall(r'role=["\'][^"\']+["\']', html, re.IGNORECASE)
    if roles:
        rep.passes.append(f"{len(roles)} ARIA role var")

    return rep
