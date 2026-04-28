"""Aylık WhatsApp kampanyası — tüm ay boyunca lead analiz et, ay sonunda top 3 seç."""
import json
import os
from pathlib import Path
from loguru import logger

_WA_MONTHLY_FILE = Path("memory/wa_monthly_contacts.json")


def _load_monthly_contacts() -> dict:
    if _WA_MONTHLY_FILE.exists():
        try:
            return json.loads(_WA_MONTHLY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_monthly_contacts(data: dict):
    _WA_MONTHLY_FILE.parent.mkdir(exist_ok=True)
    tmp = _WA_MONTHLY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, _WA_MONTHLY_FILE)


def _score_lead(rec) -> float:
    stage_scores = {
        "replied":       10.0,
        "followed_up2":   6.0,
        "followed_up":    4.0,
        "contacted":      2.0,
        "new":            1.0,
        "bounced":       -5.0,
        "unsubscribed": -10.0,
        "closed_won":   -99.0,  # zaten müşteri, WA atmaya gerek yok
        "closed_lost":   -5.0,
    }
    score = stage_scores.get(rec.stage, 0.0)
    if getattr(rec, "phone", ""):
        score += 3.0
    event_count = len(rec.events) if hasattr(rec, "events") else 0
    score += min(event_count * 0.5, 3.0)
    return score


def select_monthly_wa_leads(top_n: int = 3) -> list:
    """Bu ay WA atmak için top_n lead seç — daha önce aylık WA atılanları atla."""
    from core.lead_state import get_tracker
    tracker = get_tracker()
    monthly = _load_monthly_contacts()

    all_wa_emailed: set[str] = set()
    for month_data in monthly.values():
        for entry in month_data:
            all_wa_emailed.add(entry.get("email", "").lower())

    candidates = []
    for email, rec in list(tracker._leads.items()):
        if email in all_wa_emailed:
            continue
        if rec.stage in ("bounced", "unsubscribed", "closed_lost", "closed_won"):
            continue
        if not getattr(rec, "phone", ""):
            continue
        score = _score_lead(rec)
        candidates.append((score, rec))

    candidates.sort(key=lambda x: x[0], reverse=True)
    selected = [rec for _, rec in candidates[:top_n]]
    logger.info(f"Aylık WA seçimi: {len(candidates)} aday → {len(selected)} seçildi")
    return selected


def record_monthly_wa_sent(year: int, month: int, leads: list):
    """Bu ay WA atılan leadleri kaydet."""
    monthly = _load_monthly_contacts()
    key = f"{year}-{month:02d}"
    monthly[key] = [
        {
            "email": rec.email,
            "name": rec.name,
            "sector": rec.sector,
            "location": rec.location,
            "phone": getattr(rec, "phone", ""),
        }
        for rec in leads
    ]
    _save_monthly_contacts(monthly)
    logger.info(f"Aylık WA kaydı güncellendi: {key} → {len(leads)} lead")


def get_monthly_wa_stats() -> str:
    monthly = _load_monthly_contacts()
    if not monthly:
        return "Henüz aylık WA kampanyası yok."
    lines = []
    for month_key in sorted(monthly.keys(), reverse=True)[:12]:
        entries = monthly[month_key]
        names = ", ".join(e.get("name", "?") for e in entries)
        lines.append(f"• {month_key}: {len(entries)} kişi — {names}")
    return "Aylık WA Kampanyaları:\n" + "\n".join(lines)
