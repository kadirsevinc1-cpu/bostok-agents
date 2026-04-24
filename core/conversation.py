"""
Kullanıcı ile agent köyü arasındaki konuşma yöneticisi.
Telegram'dan gelen mesajları doğru agent'a yönlendirir.
"""
from loguru import logger
from core.message_bus import bus, AgentName, MessageType, Message


# Aktif iş takibi
_active_jobs: dict[str, dict] = {}  # job_id → {task, status, agent}


async def route_user_message(text: str, send_fn):
    """
    Telegram'dan gelen mesajı analiz edip doğru yere ilet.
    send_fn: kullanıcıya mesaj gönderen async fonksiyon
    """
    text = text.strip()
    lower = text.lower()

    # ── Komutlar ────────────────────────────────────────────────
    if text == "/yardim" or text == "/help":
        await send_fn(
            "<b>Bostok Agent Koyu Komutlari</b>\n\n"
            "<b>Bilgi:</b>\n"
            "/durum — Aktif isleri goster\n"
            "/butce — Token harcama raporu\n"
            "/inbox — Son gelen yanitlari listele\n"
            "/istatistik — Sistem ozeti\n"
            "/yardim — Bu mesaj\n\n"
            "<b>Yonetim:</b>\n"
            "/durdur — Mevcut isi durdur\n\n"
            "<b>Musteri talebi gondermek icin</b> direkt yaz:\n"
            "<i>Ornek: Bir avukat icin web sitesi yapilsin...</i>\n\n"
            "<b>Agentlere not/duzeltme gondermek icin:</b>\n"
            "<i>not: fiyati duser yap</i>\n"
            "<i>duzelt: rengi mavi yap</i>\n"
            "<i>hata: form calismıyor</i>"
        )
        return

    if text == "/inbox":
        await _show_inbox(send_fn)
        return

    if text == "/istatistik":
        await _show_stats(send_fn)
        return

    if lower.startswith("/seo "):
        url = text[5:].strip()
        if not url:
            await send_fn("Kullanim: /seo https://siteadresi.com")
            return
        await send_fn(f"⏳ Analiz ediliyor: {url}")
        try:
            from integrations.seo_analyzer import analyze as seo_analyze
            report = await seo_analyze(url)
            await send_fn(report.telegram_summary())
        except Exception as e:
            await send_fn(f"Analiz hata: {e}")
        return

    if text == "/durum":
        if not _active_jobs:
            await send_fn("Aktif is yok.")
        else:
            lines = []
            for jid, job in _active_jobs.items():
                lines.append(f"• [{jid}] {job['task'][:50]} → {job['status']}")
            await send_fn("Aktif isler:\n" + "\n".join(lines))
        return

    if text == "/durdur":
        _active_jobs.clear()
        await send_fn("Tum aktif isler durduruldu.")
        return

    # ── Lead'e yanıt gönder ────────────────────────────────────
    if lower.startswith("yanit "):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            await send_fn("Kullanim: yanit <id> <mesajiniz>\nOrnek: yanit a1b2c3 Merhaba, teklif icin musaitim.")
            return
        reply_id = parts[1].strip().lower()
        body = parts[2].strip()
        await _send_lead_reply(reply_id, body, send_fn)
        return

    # ── Agente not/düzeltme/hata ───────────────────────────────
    if any(lower.startswith(p) for p in ["not:", "duzelt:", "hata:", "degistir:", "ekle:"]):
        prefix = text.split(":")[0]
        content = text[len(prefix)+1:].strip()
        logger.info(f"Kullanici notu: [{prefix}] {content}")
        await bus.send(Message(
            sender=AgentName.SYSTEM,
            receiver=AgentName.MANAGER,
            type=MessageType.STATUS,
            content=f"[KULLANICI {prefix.upper()}] {content}",
            metadata={"user_note": True, "note_type": prefix},
        ))
        await send_fn(f"Notun Yonetici'ye iletildi: {content[:80]}")
        return

    # ── Onay/Red metin olarak ─────────────────────────────────
    if lower in ["evet", "onayla", "tamam", "ok", "yayinla"]:
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.MANAGER,
            type=MessageType.APPROVAL, content="Kullanici onayladi.",
        ))
        await send_fn("Onay verildi!")
        return

    if lower in ["hayir", "reddet", "iptal", "vazgec"]:
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.MANAGER,
            type=MessageType.STATUS,
            content="[KULLANICI RED] Islem reddedildi.",
            metadata={"rejected": True},
        ))
        await send_fn("Islem reddedildi.")
        return

    # ── Yeni müşteri talebi ────────────────────────────────────
    import uuid
    job_id = uuid.uuid4().hex[:6]
    _active_jobs[job_id] = {"task": text, "status": "Baslatildi"}
    logger.info(f"Yeni gorev [{job_id}]: {text[:60]}")

    await send_fn(
        f"Gorev alindi! [#{job_id}]\n"
        f"Agentler calismaya basladi...\n\n"
        f"<i>Not gondermek icin: not: mesajin</i>"
    )
    await bus.send(Message(
        sender=AgentName.SYSTEM, receiver=AgentName.MANAGER,
        type=MessageType.CLIENT_REQUEST, content=text,
        metadata={"job_id": job_id},
    ))


async def _send_lead_reply(reply_id: str, body: str, send_fn):
    import json
    from pathlib import Path
    from integrations.gmail import get_gmail

    inbox_file = Path("memory/inbox_emails.json")
    if not inbox_file.exists():
        await send_fn(f"Yanit bulunamadi: {reply_id}")
        return

    try:
        emails = json.loads(inbox_file.read_text(encoding="utf-8"))
    except Exception:
        await send_fn("Inbox dosyasi okunamadi.")
        return

    if reply_id not in emails:
        await send_fn(f"Yanit bulunamadi: {reply_id}\nMevcut ID'ler: {', '.join(list(emails)[-5:])}")
        return

    data = emails[reply_id]
    to = data["from_email"]
    original_subject = data.get("subject", "")
    in_reply_to = data.get("matched_message_id", "")

    subject = original_subject if original_subject.lower().startswith("re:") else f"Re: {original_subject}"

    gmail = get_gmail()
    if not gmail:
        await send_fn("Gmail bagli degil.")
        return

    ok = await gmail.send_reply(to, subject, body, in_reply_to)
    if ok:
        lead_name = data.get("sent_info", {}).get("name", to)
        await send_fn(f"✅ Yanit gonderildi: {lead_name} &lt;{to}&gt;")
    else:
        await send_fn(f"❌ Yanit gonderilemedi: {to} (limit dolmus olabilir)")


def update_job_status(job_id: str, status: str):
    if job_id in _active_jobs:
        _active_jobs[job_id]["status"] = status


async def _show_stats(send_fn):
    import json
    from pathlib import Path
    from core.budget import budget

    sent_ids   = Path("memory/sent_message_ids.json")
    inbox_file = Path("memory/inbox_emails.json")
    followup   = Path("memory/followup_log.json")

    sent_count     = len(json.loads(sent_ids.read_text(encoding="utf-8"))) if sent_ids.exists() else 0
    reply_count    = len(json.loads(inbox_file.read_text(encoding="utf-8"))) if inbox_file.exists() else 0
    followup_data  = json.loads(followup.read_text(encoding="utf-8")) if followup.exists() else {}
    f1 = sum(1 for v in followup_data.values() if v.get("f1_sent"))
    f2 = sum(1 for v in followup_data.values() if v.get("f2_sent"))

    reply_rate = f"{reply_count/sent_count*100:.1f}%" if sent_count else "—"

    await send_fn(
        f"<b>Sistem Istatistikleri</b>\n\n"
        f"Gonderilen email: <b>{sent_count}</b>\n"
        f"Gelen yanit: <b>{reply_count}</b>\n"
        f"Yanit orani: <b>{reply_rate}</b>\n\n"
        f"Follow-up (7. gun): <b>{f1}</b>\n"
        f"Follow-up (14. gun): <b>{f2}</b>\n\n"
        f"{budget.report()}"
    )


async def _show_inbox(send_fn):
    import json
    from pathlib import Path

    inbox_file = Path("memory/inbox_emails.json")
    if not inbox_file.exists():
        await send_fn("Henuz gelen yanit yok.")
        return

    try:
        emails = json.loads(inbox_file.read_text(encoding="utf-8"))
    except Exception:
        await send_fn("Inbox dosyasi okunamadi.")
        return

    if not emails:
        await send_fn("Henuz gelen yanit yok.")
        return

    items = list(emails.items())[-10:]  # Son 10
    lines = ["<b>Son Gelen Yanitlar:</b>\n"]
    for reply_id, data in reversed(items):
        from_name = data.get("from_name") or data.get("from_email", "?")
        subject = data.get("subject", "")[:40]
        sent = data.get("sent_info", {})
        sector = sent.get("sector", "")
        location = sent.get("location", "")
        received = data.get("received_at", "")[:10]
        lines.append(
            f"[<code>{reply_id}</code>] <b>{from_name}</b>\n"
            f"  {subject}\n"
            f"  {sector} — {location}  {received}\n"
            f"  <i>yanit {reply_id} mesajiniz...</i>"
        )

    await send_fn("\n\n".join(lines))
