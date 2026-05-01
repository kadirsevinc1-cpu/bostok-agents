"""Spam score checker — email gönderilmeden önce içerik kalitesini ölç."""
import re

_SPAM_WORDS = {
    # Ticari baskı
    "free!", "click here", "act now", "limited time", "urgent", "winner",
    "congratulations", "guaranteed", "no risk", "risk free", "100% free",
    "make money", "earn money", "earn $", "double your", "increase sales",
    "best price", "lowest price", "save big", "special promotion",
    # Abartı
    "amazing", "incredible", "unbelievable", "revolutionary",
    # Spam tetikleyiciler
    "dear friend", "dear sir/madam", "to whom it may concern",
    "click below", "click now", "buy now", "order now", "subscribe now",
    "call now", "apply now", "sign up free",
    # Para
    "$$$", "cash", "prize", "jackpot", "loan", "mortgage",
    # Sağlık/diyet spam
    "lose weight", "weight loss", "diet",
    # Teknik spam
    "this is not spam", "remove me", "opt-out",
}

_CAPS_WORDS_RE = re.compile(r'\b[A-Z]{3,}\b')
_EXCL_RE = re.compile(r'!')
_LINK_RE = re.compile(r'https?://')


def spam_score(text: str) -> tuple[int, list[str]]:
    """
    Return (score, issues).
    score 0-1: OK
    score 2-3: risky — consider rewriting
    score 4+:  likely spam — rewrite
    """
    issues: list[str] = []
    lower = text.lower()

    # Spam kelimeleri
    hits = [w for w in _SPAM_WORDS if w in lower]
    if hits:
        issues.append(f"Spam words detected: {', '.join(hits[:5])}")

    # ALL CAPS kelimeler
    caps = _CAPS_WORDS_RE.findall(text)
    if len(caps) > 3:
        issues.append(f"Too many all-caps words: {len(caps)} ({', '.join(caps[:4])})")

    # Ünlem işaretleri
    excl = len(_EXCL_RE.findall(text))
    if excl > 2:
        issues.append(f"Too many exclamation marks: {excl}")

    # Link sayısı
    links = len(_LINK_RE.findall(text))
    if links > 3:
        issues.append(f"Too many links: {links}")

    # Çok kısa mail (< 50 kelime) — spam gibi görünür
    word_count = len(text.split())
    if word_count < 30:
        issues.append(f"Email too short: {word_count} words")

    return len(issues), issues
