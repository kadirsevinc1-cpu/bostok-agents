"""Sektör + şehir bazlı kampanya performans takibi."""
import json
from pathlib import Path
from datetime import datetime

_PATH = Path("memory/performance.json")


def _load() -> dict:
    if not _PATH.exists():
        return {}
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict) -> None:
    _PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _key(sector: str, location: str) -> str:
    return f"{sector.strip()}||{location.strip()}"


def _get_entry(data: dict, sector: str, location: str) -> dict:
    k = _key(sector, location)
    if k not in data:
        data[k] = {"sector": sector, "location": location,
                   "sent": 0, "replied": 0, "bounced": 0, "updated_at": ""}
    return data[k]


def record_sent(sector: str, location: str) -> None:
    if not sector:
        return
    data = _load()
    e = _get_entry(data, sector, location)
    e["sent"] += 1
    e["updated_at"] = datetime.now().isoformat()
    _save(data)


def record_reply(sector: str, location: str) -> None:
    if not sector:
        return
    data = _load()
    e = _get_entry(data, sector, location)
    e["replied"] += 1
    e["updated_at"] = datetime.now().isoformat()
    _save(data)


def record_bounce(sector: str, location: str) -> None:
    if not sector:
        return
    data = _load()
    e = _get_entry(data, sector, location)
    e["bounced"] += 1
    e["updated_at"] = datetime.now().isoformat()
    _save(data)


def _reply_rate(e: dict) -> float:
    return e["replied"] / e["sent"] if e["sent"] >= 5 else -1.0


def get_best_combos(n: int = 5) -> list[dict]:
    data = _load()
    entries = [e for e in data.values() if e["sent"] >= 5]
    return sorted(entries, key=lambda e: _reply_rate(e), reverse=True)[:n]


def get_worst_combos(n: int = 5) -> list[dict]:
    data = _load()
    entries = [e for e in data.values() if e["sent"] >= 5]
    return sorted(entries, key=lambda e: _reply_rate(e))[:n]


def get_top_sectors(n: int = 5) -> list[tuple[str, float]]:
    """Sektör bazlı ortalama yanıt oranı."""
    from collections import defaultdict
    data = _load()
    sector_stats: dict = defaultdict(lambda: {"sent": 0, "replied": 0})
    for e in data.values():
        s = e["sector"]
        sector_stats[s]["sent"] += e["sent"]
        sector_stats[s]["replied"] += e["replied"]
    result = []
    for s, v in sector_stats.items():
        if v["sent"] >= 5:
            result.append((s, v["replied"] / v["sent"]))
    return sorted(result, key=lambda x: -x[1])[:n]


def format_report() -> str:
    data = _load()
    if not data:
        return "📊 Henüz yeterli performans verisi yok (en az 5 gönderim gerekli)."

    total_sent    = sum(e["sent"]    for e in data.values())
    total_replied = sum(e["replied"] for e in data.values())
    total_bounced = sum(e["bounced"] for e in data.values())
    overall_rate  = f"{total_replied / total_sent * 100:.1f}%" if total_sent else "—"

    best  = get_best_combos(5)
    worst = get_worst_combos(3)
    top_s = get_top_sectors(5)

    def fmt(e):
        rate = _reply_rate(e)
        rate_str = f"{rate * 100:.1f}%" if rate >= 0 else "veri az"
        return f"  • {e['sector']} / {e['location']}: {rate_str} ({e['sent']} mail)"

    best_lines  = "\n".join(fmt(e) for e in best)  or "  Veri yok"
    worst_lines = "\n".join(fmt(e) for e in worst) or "  Veri yok"
    sector_lines = "\n".join(
        f"  • {s}: {r * 100:.1f}%" for s, r in top_s
    ) or "  Veri yok"

    return (
        f"<b>📈 Kampanya Performans Raporu</b>\n\n"
        f"<b>Genel:</b> {total_sent} mail → {total_replied} yanıt ({overall_rate}) | bounce: {total_bounced}\n\n"
        f"<b>🏆 En İyi Kombinasyonlar</b>\n{best_lines}\n\n"
        f"<b>📉 En Düşük Performans</b>\n{worst_lines}\n\n"
        f"<b>🎯 Sektör Sıralaması</b>\n{sector_lines}"
    )
