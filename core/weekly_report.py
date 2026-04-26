"""Haftalık kampanya raporu — sent/reply/bounce istatistikleri."""
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

SENT_FILE   = Path("memory/sent_message_ids.json")
INBOX_FILE  = Path("memory/inbox_emails.json")
LEADS_FILE  = Path("memory/lead_states.json")
BOUNCE_FILE = Path("memory/bounced_emails.txt")


def _load_json(path: Path) -> dict | list:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def generate(days: int = 7) -> str:
    since = datetime.now() - timedelta(days=days)
    sent_data: dict = _load_json(SENT_FILE)
    inbox_data: dict = _load_json(INBOX_FILE)
    leads_data: dict = _load_json(LEADS_FILE)

    bounced: set = set()
    if BOUNCE_FILE.exists():
        bounced = {l.strip() for l in BOUNCE_FILE.read_text(encoding="utf-8").splitlines() if l.strip()}

    # ── Gönderilen mailler ────────────────────────────────────────
    recent_sent = []
    sector_counter: Counter = Counter()
    city_counter: Counter = Counter()
    lang_counter: Counter = Counter()

    for info in sent_data.values():
        ts_str = info.get("sent_at", "")
        try:
            ts = datetime.fromisoformat(ts_str)
        except Exception:
            ts = since  # bilinmiyorsa sayıma dahil et
        if ts >= since:
            recent_sent.append(info)
            sector_counter[info.get("sector", "?")] += 1
            city_counter[info.get("location", "?")] += 1
            lang_counter[info.get("lang", "?")] += 1

    total_sent = len(recent_sent)

    # ── Yanıtlar ─────────────────────────────────────────────────
    recent_replies = []
    intent_counter: Counter = Counter()
    for entry in inbox_data.values():
        ts_str = entry.get("received_at", "")
        try:
            ts = datetime.fromisoformat(ts_str)
        except Exception:
            continue
        if ts >= since:
            recent_replies.append(entry)
            si = entry.get("sent_info", {})
            intent_counter[si.get("intent", "unknown")] += 1

    total_replies = len(recent_replies)

    # ── Lead aşamaları ────────────────────────────────────────────
    stage_counter: Counter = Counter()
    for lead in leads_data.values():
        stage_counter[lead.get("stage", "?")] += 1

    # ── Bounce ───────────────────────────────────────────────────
    total_bounced = len(bounced)

    # ── Oranlar ──────────────────────────────────────────────────
    reply_rate = f"{total_replies / total_sent * 100:.1f}%" if total_sent else "—"
    bounce_rate = f"{total_bounced / max(len(sent_data), 1) * 100:.1f}%"

    # ── En iyi 3 sektör / şehir ───────────────────────────────────
    top_sectors = sector_counter.most_common(3)
    top_cities  = city_counter.most_common(3)
    top_langs   = lang_counter.most_common(3)

    sector_lines = "\n".join(f"  • {s}: {n}" for s, n in top_sectors) or "  Veri yok"
    city_lines   = "\n".join(f"  • {c}: {n}" for c, n in top_cities)  or "  Veri yok"
    lang_line    = " | ".join(f"{l}:{n}" for l, n in top_langs) or "—"

    # ── Lead aşama özeti ──────────────────────────────────────────
    stage_lines = "\n".join(
        f"  {s}: {n}" for s, n in sorted(stage_counter.items(), key=lambda x: -x[1])
    ) or "  Veri yok"

    label = f"Son {days} Gün" if days < 30 else "Genel"
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    return (
        f"<b>📊 Bostok Kampanya Raporu — {label}</b>\n"
        f"<i>{now_str}</i>\n\n"
        f"<b>📬 Gönderim</b>\n"
        f"Toplam mail: <b>{total_sent}</b>\n"
        f"Yanıt: <b>{total_replies}</b> ({reply_rate})\n"
        f"Bounce: {total_bounced} ({bounce_rate})\n\n"
        f"<b>🏆 En Aktif Sektörler</b>\n{sector_lines}\n\n"
        f"<b>🏙️ En Aktif Şehirler</b>\n{city_lines}\n\n"
        f"<b>🌐 Dil Dağılımı</b>\n{lang_line}\n\n"
        f"<b>📋 Lead Aşamaları</b>\n{stage_lines}"
    )
