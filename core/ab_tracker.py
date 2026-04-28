"""A/B test sonuç takibi — hangi konu satırı pattern'i daha çok yanıt alıyor."""
import json
import os
import re
from datetime import datetime
from pathlib import Path

AB_FILE = Path("memory/ab_results.json")


def _load() -> dict:
    if AB_FILE.exists():
        try:
            return json.loads(AB_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(data: dict):
    AB_FILE.parent.mkdir(exist_ok=True)
    tmp = AB_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, AB_FILE)


def record_sent(msg_id: str, subject: str, sector: str, lang: str):
    """Gönderilen mail konusunu kaydet."""
    data = _load()
    data[msg_id] = {
        "subject": subject,
        "sector": sector,
        "lang": lang,
        "sent_at": datetime.now().isoformat(),
        "replied": False,
    }
    _save(data)


def record_reply(msg_id: str):
    """Bu msg_id'ye yanıt geldi — başarılı olarak işaretle."""
    data = _load()
    if msg_id in data:
        data[msg_id]["replied"] = True
        data[msg_id]["replied_at"] = datetime.now().isoformat()
        _save(data)


def get_top_patterns(n: int = 5) -> list[dict]:
    """En yüksek yanıt oranına sahip konu pattern'lerini döndür."""
    data = _load()
    if not data:
        return []

    # Konu başına gönderim + yanıt sayısı
    counts: dict[str, dict] = {}
    for entry in data.values():
        subj = entry.get("subject", "").strip()
        if not subj or len(subj) < 5:
            continue
        if subj not in counts:
            counts[subj] = {"sent": 0, "replies": 0}
        counts[subj]["sent"] += 1
        if entry.get("replied"):
            counts[subj]["replies"] += 1

    results = []
    for subj, c in counts.items():
        if c["sent"] >= 3:  # En az 3 kez gönderilmiş konuları değerlendir
            rate = c["replies"] / c["sent"] * 100
            results.append({
                "subject": subj,
                "sent": c["sent"],
                "replies": c["replies"],
                "rate": rate,
            })

    results.sort(key=lambda x: (-x["replies"], -x["rate"]))
    return results[:n]


def get_prompt_hint(sector: str = "", lang: str = "") -> str:
    """Prompt için en iyi konu pattern'lerini kısa metin olarak döndür."""
    patterns = get_top_patterns(3)
    if not patterns:
        return ""
    lines = [f'"{p["subject"]}" ({p["replies"]} yanıt / {p["sent"]} gönderim)'
             for p in patterns if p["replies"] > 0]
    if not lines:
        return ""
    return "Geçmişte iyi sonuç veren konu formatları:\n" + "\n".join(lines)


def cleanup_old(days: int = 90):
    """90 günden eski, yanıtsız kayıtları temizle."""
    data = _load()
    cutoff = datetime.now().timestamp() - days * 86400
    cleaned = {
        k: v for k, v in data.items()
        if v.get("replied") or
        datetime.fromisoformat(v.get("sent_at", "2000-01-01")).timestamp() > cutoff
    }
    if len(cleaned) < len(data):
        _save(cleaned)
