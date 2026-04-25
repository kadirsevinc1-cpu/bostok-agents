"""
HTML Validator Skill — lxml/html.parser ile gerçek yapısal hata tespiti.
LLM kullanmaz (0 token). Hataları QA agent'ın prompt'una ekler.
"""
from dataclasses import dataclass, field
from html.parser import HTMLParser

_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
         "link", "meta", "param", "source", "track", "wbr"}


class _Validator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self._stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag not in _VOID:
            self._stack.append(tag)

        if tag == "img" and "alt" not in attrs_dict:
            src = attrs_dict.get("src", "?")[:40]
            self.warnings.append(f"<img> alt eksik (src={src})")

        if tag == "form" and "action" not in attrs_dict:
            self.warnings.append("<form> action attribute eksik")

        if tag == "a" and "href" not in attrs_dict:
            self.warnings.append("<a> href attribute eksik")

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
        else:
            self.errors.append(f"Beklenmeyen kapanış: </{tag}>")

    def unclosed(self) -> list[str]:
        return self._stack[:]


@dataclass
class HTMLReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def has_critical(self) -> bool:
        return len(self.errors) > 0

    def summary(self) -> str:
        if not self.errors and not self.warnings:
            return "✅ HTML yapısı geçerli"
        lines = [f"❌ {e}" for e in self.errors[:5]]
        lines += [f"⚠️ {w}" for w in self.warnings[:5]]
        return "\n".join(lines)


def validate_html(html: str) -> HTMLReport:
    report = HTMLReport()
    v = _Validator()
    try:
        v.feed(html)
    except Exception as e:
        report.errors.append(f"Parse hatası: {e}")
        return report

    report.errors.extend(v.errors[:8])
    report.warnings.extend(v.warnings[:8])

    for tag in v.unclosed()[-5:]:
        report.errors.append(f"Kapatılmamış: <{tag}>")

    return report
