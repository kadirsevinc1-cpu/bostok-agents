"""
Skill Crystallizer — GenericAgent'tan ilham alınmıştır (MIT).
Başarılı outreach pattern'larını kaydeder ve marketing agent tarafından
okunarak gelecekteki emailleri bilinçli yönlendirir.
"""
import json
from datetime import datetime
from pathlib import Path

_FILE = Path("memory/successful_patterns.json")
_MAX_PATTERNS = 200


def _load() -> list[dict]:
    if _FILE.exists():
        try:
            return json.loads(_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save(patterns: list[dict]) -> None:
    _FILE.parent.mkdir(exist_ok=True)
    tmp = _FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(patterns, ensure_ascii=False, indent=2), encoding="utf-8")
    import os
    os.replace(tmp, _FILE)


def record_success(sector: str, location: str, lang: str, intent: str,
                   has_website: bool, subject: str = "") -> None:
    """Pozitif yanıt geldiğinde çağrılır — pattern'ı kristalleştirir."""
    patterns = _load()
    patterns.append({
        "sector":      sector,
        "location":    location,
        "lang":        lang,
        "intent":      intent,
        "has_website": has_website,
        "subject":     subject[:120] if subject else "",
        "recorded_at": datetime.now().isoformat(),
    })
    # Yalnızca son N pattern'ı tut
    _save(patterns[-_MAX_PATTERNS:])


def get_success_hints(sector: str, lang: str) -> str:
    """
    Marketing agent için: bu sektör+dil kombinasyonunda
    daha önce ne işe yaradığını özetle.
    """
    patterns = _load()
    relevant = [
        p for p in patterns
        if p.get("sector", "").lower() == sector.lower()
        and p.get("lang", "") == lang
    ]
    if not relevant:
        return ""

    total = len(relevant)
    by_intent: dict[str, int] = {}
    for p in relevant:
        by_intent[p["intent"]] = by_intent.get(p["intent"], 0) + 1

    # Başarılı konu örnekleri (en fazla 3)
    subjects = [p["subject"] for p in relevant if p.get("subject")][:3]

    lines = [f"[Pattern memory: {total} positive reply(ies) for {sector}/{lang}]"]
    for intent, count in sorted(by_intent.items(), key=lambda x: -x[1]):
        lines.append(f"  - {intent}: {count}x")
    if subjects:
        lines.append("  Successful subject examples:")
        for s in subjects:
            lines.append(f"    • {s}")
    return "\n".join(lines)


def get_stats() -> dict:
    """Genel istatistik — haftalık rapor için."""
    patterns = _load()
    if not patterns:
        return {"total": 0}
    by_sector: dict[str, int] = {}
    by_lang: dict[str, int] = {}
    for p in patterns:
        s = p.get("sector", "unknown")
        l = p.get("lang", "?")
        by_sector[s] = by_sector.get(s, 0) + 1
        by_lang[l] = by_lang.get(l, 0) + 1
    return {
        "total": len(patterns),
        "by_sector": by_sector,
        "by_lang": by_lang,
    }
