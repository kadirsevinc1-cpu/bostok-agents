"""
Bostok Agent Köyü — Ana başlatıcı.
Kullanım:
  python main.py                          # demo görevi
  python main.py "Müşteri talebi buraya" # özel görev
"""
import asyncio
import sys
from loguru import logger
from core.message_bus import bus, AgentName, MessageType, Message
from core.budget import budget
from agents.manager import ManagerAgent
from agents.analyst import AnalystAgent
from agents.marketing import MarketingAgent
from agents.quote import QuoteAgent
from agents.content import ContentAgent
from agents.designer import DesignerAgent
from agents.developer import DeveloperAgent
from agents.qa import QAAgent
from agents.deploy import DeployAgent
from agents.inbox_watcher import InboxWatcherAgent
from agents.followup import FollowupAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.whatsapp_agent import WhatsAppAgent
from agents.lead_scout import LeadScoutAgent
from agents.linkedin_agent import LinkedInAgent
from agents.competitor_analyst import CompetitorAnalystAgent
from core.campaigns import CAMPAIGNS
from integrations.telegram import init_bot, get_bot
from integrations.gmail import init_gmail
from integrations.gmail_reader import init_reader
from integrations.netlify import init_netlify
from integrations.whatsapp import init_whatsapp


def setup_logging():
    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")
    logger.add("memory/bostok.log", rotation="10 MB", level="DEBUG")


async def budget_monitor():
    while True:
        await asyncio.sleep(300)
        report = budget.report()
        logger.info(f"\n{report}")
        if budget.is_blocked():
            logger.error("BUTCE LIMITI ASILDI!")
            bot = get_bot()
            if bot:
                await bot.send("Gunluk token limiti asildi. Sistem durduruldu.")
            await bus.send(Message(
                sender=AgentName.SYSTEM, receiver=AgentName.MANAGER,
                type=MessageType.BUDGET_ALERT,
                content="Gunluk token limiti asildi.",
            ))





async def notify_handler(msg: Message):
    """Bildirimleri hem konsola bas hem Telegram'a gönder."""
    if msg.type != MessageType.USER_NOTIFY:
        return

    # Konsola yaz
    print(f"\n{'='*60}")
    print(f"BILDIRIM [{msg.sender.value}]:")
    print(msg.content)
    print('='*60)

    # Telegram'a gönder
    bot = get_bot()
    if not bot:
        return

    requires_approval = msg.metadata.get("requires_approval", False)

    if requires_approval:
        # Onay butonu ile gönder
        import uuid
        approval_id = uuid.uuid4().hex[:8]
        approved = await bot.request_approval(approval_id, msg.content)
        if approved:
            await bus.send(Message(
                sender=AgentName.SYSTEM, receiver=AgentName.MANAGER,
                type=MessageType.APPROVAL, content="Kullanici onayi alindi.",
            ))
        else:
            await bot.send("Islem iptal edildi.")
    else:
        await bot.send(msg.content)


async def handle_telegram_message(text: str):
    """Telegram'dan gelen mesajı akıllı router'a ilet."""
    from core.conversation import route_user_message
    from integrations.gmail import load_bounced
    bot = get_bot()

    cmd = text.strip().lower()

    if cmd == "/butce":
        if bot:
            await bot.send(budget.report())
        return

    if cmd == "/durum":
        if bot:
            from agents.marketing import _get_demo_base, _WORKER_BASE
            _durum_loop = asyncio.get_running_loop()
            demo = await _durum_loop.run_in_executor(None, _get_demo_base)
            demo_src = "Vercel" if "vercel.app" in demo else ("Worker" if demo == _WORKER_BASE else "Netlify")
            bounced = len(load_bounced())
            from pathlib import Path
            sent = len(Path("memory/sent_emails.txt").read_text(encoding="utf-8").splitlines()) if Path("memory/sent_emails.txt").exists() else 0
            import json
            inbox = len(json.loads(Path("memory/inbox_emails.json").read_text(encoding="utf-8"))) if Path("memory/inbox_emails.json").exists() else 0
            b = budget.daily_usage()

            # Lead lifecycle özeti
            try:
                from core.lead_state import get_tracker
                stage_summary = get_tracker().summary()
                stage_labels = {
                    "new": "Yeni", "contacted": "Maillendi", "followed_up": "Takip1",
                    "followed_up2": "Takip2", "replied": "Yanıtladı", "bounced": "Bounce",
                    "unsubscribed": "İptal", "closed_won": "Müşteri", "closed_lost": "Kapandı",
                }
                lead_lines = "\n".join(
                    f"  • {stage_labels.get(s, s)}: {c}"
                    for s, c in sorted(stage_summary.items(), key=lambda x: x[1], reverse=True)
                ) or "  Henüz veri yok"
            except Exception:
                lead_lines = "  Veri okunamadı"

            try:
                from core.campaign_state import exhausted_count
                exhausted = exhausted_count()
            except Exception:
                exhausted = 0

            msg = (
                f"<b>Sistem Durumu</b>\n\n"
                f"<b>LLM:</b> {b['requests']} istek, {b['tokens_used']:,} token kullanıldı\n"
                f"<b>Bütçe:</b> {'⛔ BLOKE' if b['blocked'] else '✅ Normal'} ({b['tokens_used']/50000:.1f}%)\n\n"
                f"<b>Mail:</b>\n"
                f"  • Gönderilen: {sent}\n"
                f"  • Gelen yanıt: {inbox}\n"
                f"  • Bounce (geçersiz): {bounced}\n\n"
                f"<b>Lead Aşamaları:</b>\n{lead_lines}\n\n"
                f"<b>Kampanya:</b> 201 kombinasyon, {exhausted} tükendi (90g atlanacak)\n\n"
                f"<b>Demo site:</b> {demo_src}\n{demo[:60]}"
            )
            await bot.send(msg)
        return

    if cmd == "/istatistik":
        if bot:
            from pathlib import Path
            import json
            sent_ids = json.loads(Path("memory/sent_message_ids.json").read_text(encoding="utf-8")) if Path("memory/sent_message_ids.json").exists() else {}
            by_sector: dict = {}
            by_lang: dict = {}
            for info in sent_ids.values():
                s = info.get("sector", "?")
                l = info.get("lang", "?")
                by_sector[s] = by_sector.get(s, 0) + 1
                by_lang[l]   = by_lang.get(l, 0) + 1
            top_sectors = sorted(by_sector.items(), key=lambda x: -x[1])[:5]
            langs_str = " | ".join(f"{l}:{n}" for l, n in sorted(by_lang.items(), key=lambda x: -x[1]))
            sector_str = "\n".join(f"  • {s}: {n}" for s, n in top_sectors)
            msg = (
                f"<b>Kampanya İstatistikleri</b>\n\n"
                f"<b>Toplam mail:</b> {len(sent_ids)}\n\n"
                f"<b>Sektörler:</b>\n{sector_str or '  Veri yok'}\n\n"
                f"<b>Diller:</b> {langs_str or 'Veri yok'}"
            )
            await bot.send(msg)
        return

    if cmd.startswith("yanit "):
        parts = text[len("yanit "):].strip().split(None, 1)
        if len(parts) < 2:
            if bot:
                await bot.send("⚠️ Kullanım: <code>yanit {reply_id} {mesaj}</code>")
            return
        reply_id, reply_text = parts[0].strip(), parts[1].strip()

        import json
        from pathlib import Path
        inbox_path = Path("memory/inbox_emails.json")
        if not inbox_path.exists():
            if bot:
                await bot.send("❌ Henüz yanıt gelen mail yok.")
            return

        inbox = json.loads(inbox_path.read_text(encoding="utf-8"))
        entry = inbox.get(reply_id)
        if not entry:
            if bot:
                await bot.send(f"❌ <code>{reply_id}</code> ID'li yanıt bulunamadı.")
            return

        from integrations.gmail import get_gmail
        gmail = get_gmail()
        if not gmail:
            if bot:
                await bot.send("❌ Gmail yapılandırılmamış.")
            return

        SIGNATURE = "\n\nSaygılar,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev"
        full_body = reply_text + SIGNATURE
        to_email = entry["from_email"]
        subject = entry.get("subject", "")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        in_reply_to = entry.get("matched_message_id", "")

        ok = await gmail.send_reply(to_email, subject, full_body, in_reply_to=in_reply_to)
        if ok:
            if bot:
                await bot.send(
                    f"✅ Yanıt gönderildi!\n"
                    f"<b>Kime:</b> {entry.get('from_name', '')} &lt;{to_email}&gt;\n"
                    f"<b>Konu:</b> {subject}"
                )
        else:
            if bot:
                await bot.send("❌ Yanıt gönderilemedi, log'ları kontrol edin.")
        return

    if cmd.startswith("revize "):
        revision_text = text[len("revize "):].strip()
        if not revision_text:
            if bot:
                await bot.send("⚠️ Kullanım: <code>revize {talimat}</code>\nÖrnek: <code>revize rengi kırmızı yap, logo büyüt</code>")
            return

        await bus.send(Message(
            sender=AgentName.SYSTEM,
            receiver=AgentName.MANAGER,
            type=MessageType.STATUS,
            content=revision_text,
            metadata={"note_type": "revizyon"},
        ))
        if bot:
            await bot.send("🔧 Revize talebi gönderildi, işleniyor...")
        return

    if cmd.startswith("/bilgi"):
        sector = text[len("/bilgi"):].strip()
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.KNOWLEDGE,
            type=MessageType.STATUS,
            content=sector or "genel",
            metadata={"cmd": "bilgi"},
        ))
        return

    if cmd.startswith("/ogret"):
        knowledge = text[len("/ogret"):].strip()
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.KNOWLEDGE,
            type=MessageType.STATUS,
            content=knowledge,
            metadata={"cmd": "ogret"},
        ))
        return

    if cmd.startswith("/pattern"):
        location = text[len("/pattern"):].strip()
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.KNOWLEDGE,
            type=MessageType.STATUS,
            content=location or "",
            metadata={"cmd": "pattern"},
        ))
        return

    if cmd == "/haftalik":
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.KNOWLEDGE,
            type=MessageType.STATUS,
            content="",
            metadata={"cmd": "haftalik"},
        ))
        return

    if cmd == "/performans":
        from core.performance_tracker import format_report as perf_report
        if bot:
            await bot.send(perf_report())
        return

    if cmd.startswith("/wp "):
        parts = text[len("/wp "):].strip().split(None, 1)
        if not parts:
            if bot:
                await bot.send("⚠️ Kullanım: <code>/wp {sektör} {şehir}</code>\nÖrnek: <code>/wp restoran İstanbul</code>")
            return
        wp_sector   = parts[0]
        wp_location = parts[1] if len(parts) > 1 else ""
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.WHATSAPP,
            type=MessageType.TASK,
            content=f"{wp_sector} {wp_location} WhatsApp kampanyası",
            metadata={"sector": wp_sector, "location": wp_location, "languages": ["tr"]},
        ))
        if bot:
            await bot.send(f"📱 WhatsApp kampanyası başlatıldı: <b>{wp_sector}</b> / {wp_location}")
        return

    if cmd == "/agents":
        if bot:
            import datetime as _dt
            from agents.base import _AGENT_REGISTRY
            now = _dt.datetime.now()
            lines = []
            for name, agent in sorted(_AGENT_REGISTRY.items()):
                diff = (now - agent.last_heartbeat).total_seconds()
                icon = "✅" if diff < 120 else ("⚠️" if diff < 600 else "❌")
                lines.append(f"{icon} <b>{name}</b> — {int(diff)}s önce aktif, {agent.loop_count:,} loop")
            from integrations.tracking_server import _public_url
            dashboard_line = f"\n\n🌐 Dashboard: {_public_url}/dashboard" if _public_url else ""
            await bot.send("<b>Agent Durumu</b>\n\n" + "\n".join(lines) + dashboard_line)
        return

    if cmd.startswith("/dizin "):
        parts = text[len("/dizin "):].strip().split(None, 1)
        if len(parts) < 2:
            if bot:
                await bot.send("⚠️ Kullanım: <code>/dizin {sektör} {şehir}</code>\nÖrnek: <code>/dizin restoran Istanbul</code>")
            return
        d_sector, d_location = parts[0], parts[1]
        if bot:
            await bot.send(f"🔍 Dizin taranıyor: <b>{d_sector}</b> / {d_location}...")
        try:
            from integrations.chamber_scraper import scrape_directory
            d_leads = await scrape_directory(d_sector, d_location)
            with_email = [l for l in d_leads if l.email]
            names = "\n".join(f"  • {l.name} — {l.email or '(email yok)'}" for l in d_leads[:10])
            await bot.send(
                f"📋 <b>Dizin Sonucu</b> ({d_sector}/{d_location})\n\n"
                f"Bulunan: {len(d_leads)} firma, {len(with_email)} email\n\n"
                f"{names}"
                + (f"\n  ... ve {len(d_leads)-10} firma daha" if len(d_leads) > 10 else "")
            )
        except Exception as e:
            if bot:
                await bot.send(f"❌ Dizin scraping hatası: {e}")
        return

    if cmd == "/wa-rapor":
        from core.monthly_wa_selector import get_monthly_wa_stats
        if bot:
            await bot.send(get_monthly_wa_stats())
        return

    if cmd == "/rapor" or cmd.startswith("/rapor "):
        days = 7
        try:
            days = int(text.split()[1]) if len(text.split()) > 1 else 7
        except (ValueError, IndexError):
            pass
        from core.weekly_report import generate as gen_report
        if bot:
            await bot.send(gen_report(days=days))
        return

    if cmd == "/stats":
        lines = ["📊 <b>Sistem İstatistikleri</b>\n"]
        # Decision log özeti
        try:
            import json
            from pathlib import Path
            dlog = Path("memory/decision_log.jsonl")
            if dlog.exists():
                entries = [json.loads(l) for l in dlog.read_text(encoding="utf-8").splitlines() if l.strip()]
                by_lang: dict = {}
                by_sector: dict = {}
                for e in entries:
                    lg = e.get("lang", "?"); by_lang[lg] = by_lang.get(lg, 0) + 1
                    sc = e.get("sector", "?")[:20]; by_sector[sc] = by_sector.get(sc, 0) + 1
                top_sectors = sorted(by_sector.items(), key=lambda x: -x[1])[:5]
                lines.append(f"📬 <b>Gönderilen Email:</b> {len(entries)} toplam")
                lines.append("  Dil: " + " | ".join(f"{k}:{v}" for k, v in sorted(by_lang.items(), key=lambda x: -x[1])))
                lines.append("  Top sektörler: " + ", ".join(f"{s}({n})" for s, n in top_sectors))
            else:
                lines.append("📬 Henüz email gönderilmedi.")
        except Exception as e:
            lines.append(f"(decision log okunamadı: {e})")

        # Skill crystallization özeti
        try:
            from core.skills.skill_crystallizer import get_stats
            cs = get_stats()
            if cs.get("total", 0) > 0:
                lines.append(f"\n✨ <b>Kristalize Pattern:</b> {cs['total']} başarılı yanıt")
                top_s = sorted(cs.get("by_sector", {}).items(), key=lambda x: -x[1])[:3]
                top_l = sorted(cs.get("by_lang", {}).items(), key=lambda x: -x[1])[:3]
                lines.append("  Sektör: " + ", ".join(f"{s}({n})" for s, n in top_s))
                lines.append("  Dil: " + " | ".join(f"{l}:{n}" for l, n in top_l))
            else:
                lines.append("\n✨ Henüz kristalize pattern yok.")
        except Exception:
            pass

        if bot:
            await bot.send("\n".join(lines))
        return

    if cmd.startswith("onayla "):
        _onayla_parts = text[len("onayla "):].strip().split()
        if not _onayla_parts:
            if bot:
                await bot.send("⚠️ Kullanım: <code>onayla {id}</code>")
            return
        reply_id = _onayla_parts[0]
        import json
        from pathlib import Path
        drafts_path = Path("memory/drafts.json")
        if not drafts_path.exists():
            if bot:
                await bot.send("❌ Onaylanacak taslak bulunamadı.")
            return
        drafts = json.loads(drafts_path.read_text(encoding="utf-8"))
        entry = drafts.get(reply_id)
        if not entry:
            if bot:
                await bot.send(f"❌ <code>{reply_id}</code> ID'li taslak bulunamadı.")
            return

        inbox_path = Path("memory/inbox_emails.json")
        inbox = json.loads(inbox_path.read_text(encoding="utf-8")) if inbox_path.exists() else {}
        inbox_entry = inbox.get(reply_id)
        if not inbox_entry:
            if bot:
                await bot.send(f"❌ Orijinal yanıt bulunamadı: <code>{reply_id}</code>")
            return

        from integrations.gmail import get_gmail
        gmail = get_gmail()
        if not gmail:
            if bot:
                await bot.send("❌ Gmail yapılandırılmamış.")
            return

        SIGNATURE = "\n\nSaygılar,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev"
        full_body = entry["draft"] + SIGNATURE
        to_email = inbox_entry["from_email"]
        subject = inbox_entry.get("subject", "")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        in_reply_to = inbox_entry.get("matched_message_id", "")

        ok = await gmail.send_reply(to_email, subject, full_body, in_reply_to=in_reply_to)
        if ok:
            # Taslağı sil
            del drafts[reply_id]
            drafts_path.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")
            if bot:
                await bot.send(
                    f"✅ Taslak onaylandı ve gönderildi!\n"
                    f"<b>Kime:</b> {inbox_entry.get('from_name', '')} &lt;{to_email}&gt;"
                )
        else:
            if bot:
                await bot.send("❌ Gönderim başarısız, log'ları kontrol edin.")
        return

    if cmd == "/profil":
        from core.user_profile import format_profile_summary
        if bot:
            await bot.send(format_profile_summary())
        return

    if cmd.startswith("/profil set "):
        # Basit alan güncelleme: /profil set notes Yeni not metni
        rest = text[len("/profil set "):].strip()
        parts = rest.split(None, 1)
        if len(parts) < 2:
            if bot:
                await bot.send("⚠️ Kullanım: <code>/profil set {alan} {değer}</code>\nÖrnek: <code>/profil set notes Yeni notum</code>")
            return
        field_key, field_val = parts[0], parts[1]
        from core.user_profile import get_profile, save_profile
        profile = get_profile()
        # Sadece üst düzey string alanları destekle
        if field_key in profile and isinstance(profile[field_key], str):
            profile[field_key] = field_val
            save_profile(profile)
            if bot:
                await bot.send(f"✅ Profil güncellendi: <b>{field_key}</b> = {field_val[:100]}")
        else:
            if bot:
                await bot.send(f"❌ Alan bulunamadı veya desteklenmiyor: <code>{field_key}</code>")
        return

    if cmd.startswith("/hunt "):
        parts = text[len("/hunt "):].strip().rsplit(None, 1)
        if len(parts) < 2:
            if bot:
                await bot.send("⚠️ Kullanım: <code>/hunt {sektör} {ülke}</code>\nÖrnek: <code>/hunt aluminium profile Germany</code>")
            return
        h_sector, h_country = parts[0].strip(), parts[1].strip()
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.COMPETITOR_ANALYST,
            type=MessageType.TASK,
            content=f"{h_sector} / {h_country} competitor analysis",
            metadata={"sector": h_sector, "country": h_country},
        ))
        return

    if cmd.startswith("/linkedin "):
        parts = text[len("/linkedin "):].strip().split(None, 1)
        if len(parts) < 2:
            if bot:
                await bot.send("⚠️ Kullanım: <code>/linkedin {sektör} {şehir}</code>\nÖrnek: <code>/linkedin restaurant Berlin</code>")
            return
        li_sector, li_location = parts[0], parts[1]
        if bot:
            await bot.send(f"🔗 LinkedIn taranıyor: <b>{li_sector}</b> / {li_location}...")
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.LINKEDIN,
            type=MessageType.TASK,
            content=f"{li_sector} {li_location} LinkedIn outreach",
            metadata={"sector": li_sector, "location": li_location, "languages": ["en"]},
        ))
        return

    if cmd == "/yardim" or cmd == "/help":
        if bot:
            await bot.send(
                "<b>Bostok Agent Köyü — Komutlar</b>\n\n"
                "/durum — Sistem durumu (token, mail, demo)\n"
                "/butce — Günlük token bütçesi\n"
                "/istatistik — Kampanya istatistikleri\n"
                "/rapor [gün] — Kampanya raporu (varsayılan: 7 gün)\n"
                "/performans — Sektör/şehir yanıt oranı analizi\n"
                "/wp {sektör} {şehir} — WhatsApp kampanyası başlat\n"
                "/wa-rapor — Aylık WA kampanya geçmişi\n"
                "/dizin {sektör} {şehir} — Dizin scraper'ı manuel tetikle\n"
                "/hunt {sektör} {ülke} — Rakip site analizi + yeni site konsepti\n"
                "/linkedin {sektör} {şehir} — LinkedIn profil bul + mesaj üret\n"
                "/stats — Gönderilen email + başarılı pattern özeti\n"
                "/agents — Tüm agent'ların sağlık durumu\n"
                "/bilgi [sektör] — Sektör bilgi tabanı\n"
                "/ogret [sektör]|[bilgi] — KB'ye bilgi ekle\n"
                "/pattern [şehir] — Öğrenilen pattern'ler\n"
                "/haftalik — Haftalık öğrenme özeti\n"
                "/yardim — Bu yardım mesajı\n\n"
                "<b>📬 Müşteri Yanıt Komutları:</b>\n"
                "yanit {id} {mesaj} — Müşteriye mail yanıtı gönder\n"
                "onayla {id} — Otomatik taslağı onayla ve gönder\n"
                "revize {talimat} — Demo sitede değişiklik talep et\n\n"
                "<b>👤 Profil Komutları:</b>\n"
                "/profil — Kullanıcı profili ve tercihler\n"
                "/profil set {alan} {değer} — Profil güncelle\n\n"
                "Veya doğrudan mesaj yaz: <i>İstanbul'daki kafeler için kampanya başlat</i>"
            )
        return

    async def send_fn(msg: str):
        if bot:
            await bot.send(msg)

    await route_user_message(text, send_fn)


async def _detect_public_ip() -> str:
    import aiohttp
    for url in ["https://api.ipify.org", "https://ifconfig.me/ip", "https://ipecho.net/plain"]:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                    ip = (await r.text()).strip()
                    if ip and "." in ip:
                        return ip
        except Exception:
            pass
    return ""


async def _wait_for_internet(timeout: int = 120):
    """İnternet bağlantısı gelene kadar bekle (max 2 dakika)."""
    import aiohttp
    for attempt in range(timeout // 5):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://api.telegram.org", timeout=aiohttp.ClientTimeout(total=4)) as r:
                    if r.status < 500:
                        if attempt > 0:
                            logger.info(f"Internet baglantisi geldi ({attempt * 5}s sonra)")
                        return
        except Exception:
            pass
        if attempt == 0:
            logger.warning("Internet baglantisi yok, bekleniyor...")
        await asyncio.sleep(5)
    logger.warning("Internet baglantisi 2 dakika icinde gelmedi, devam ediliyor")


async def main():
    setup_logging()
    # PID dosyası yaz — auto_update.sh bu dosyayı kullanarak süreci yönetir
    import os as _os
    from pathlib import Path as _Path
    _pid_file = _Path("memory/main.pid")
    _pid_file.parent.mkdir(exist_ok=True)
    _pid_file.write_text(str(_os.getpid()))
    logger.info(f"PID: {_os.getpid()} → memory/main.pid")
    logger.info("Bostok Agent Koyu baslatiliyor...")
    await _wait_for_internet()
    logger.info(budget.report())

    # Demo site deploy — Vercel (öncelikli) → Netlify → Worker fallback
    from integrations.vercel import deploy_demo_site as vercel_deploy
    vercel_url = await vercel_deploy("demo_site")
    if vercel_url:
        logger.info(f"Demo site (Vercel): {vercel_url}")
    else:
        netlify = init_netlify()
        if netlify:
            netlify_url = await netlify.deploy_demo_site("demo_site")
            if netlify_url:
                logger.info(f"Demo site (Netlify): {netlify_url}")
            else:
                logger.info("Demo site: Cloudflare Worker kullaniliyor")

    # Gmail başlat
    gmail = init_gmail()
    if gmail:
        logger.info(f"Gmail hazir: {gmail.stats}")
        from integrations.gmail import GmailPool
        _r_user = gmail._senders[0]._user if isinstance(gmail, GmailPool) else gmail._user
        _r_pass = gmail._senders[0]._password if isinstance(gmail, GmailPool) else gmail._password
        init_reader(_r_user, _r_pass)
        logger.info("Gmail inbox takibi aktif")
    else:
        logger.warning("Gmail bagli degil - sadece sablon modu")

    # Tracking sunucusu başlat (port 8080)
    from integrations.tracking_server import start as tracking_start, set_public_url
    tracking_port = 8080
    public_ip = await _detect_public_ip()
    if public_ip:
        tracking_url = f"http://{public_ip}:{tracking_port}"
        set_public_url(tracking_url)
        from integrations.gmail import get_gmail  # henüz init edilmedi, sonra set edilecek
        logger.info(f"Dashboard: {tracking_url}/dashboard")
    else:
        logger.warning("Public IP tespit edilemedi, tracking devre dışı")

    # WhatsApp başlat
    wa = init_whatsapp()
    if wa:
        logger.info("WhatsApp: Green-API bagli")

    # Telegram botu başlat
    bot = init_bot()
    if bot:
        logger.info("Telegram bagli - mesaj atabilirsiniz!")
    else:
        logger.warning("Telegram bagli degil - sadece konsol modu")

    # Bildirim listener
    bus.add_listener(notify_handler)

    # Tüm agent'ları başlat
    agents = [
        ManagerAgent(), AnalystAgent(), MarketingAgent(),
        QuoteAgent(), ContentAgent(), DesignerAgent(),
        DeveloperAgent(), QAAgent(), DeployAgent(),
        InboxWatcherAgent(), FollowupAgent(), KnowledgeAgent(),
        WhatsAppAgent(), LeadScoutAgent(), LinkedInAgent(),
        CompetitorAnalystAgent(),
    ]
    logger.info(f"{len(agents)} agent baslatildi")

    tasks = [asyncio.create_task(a.run()) for a in agents]
    tasks.append(asyncio.create_task(budget_monitor()))

    # Telegram polling başlat
    if bot:
        tasks.append(asyncio.create_task(
            bot.poll_updates(on_message=handle_telegram_message)
        ))

    # Komut satırı argümanı varsa demo görevi çalıştır
    if len(sys.argv) > 1:
        demo_task = " ".join(sys.argv[1:])
        await asyncio.sleep(1)
        logger.info(f"Demo gorevi: {demo_task}")
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.MANAGER,
            type=MessageType.CLIENT_REQUEST, content=demo_task,
        ))
        if bot:
            await bot.send(f"Gorev baslatildi: {demo_task[:100]}")

    if bot:
        await bot.send(
            "Bostok Agent Koyu aktif!\n\n"
            "Musteri talebi gondermek icin direkt yazin.\n"
            "Komutlar icin /yardim yazin."
        )
        logger.info("Hazir! Telegram'dan mesaj atabilirsiniz.")
    else:
        logger.info("Demo icin: python main.py 'musteri talebi buraya'")

    async def _embed_loop():
        """Her 10 dakikada yeni memory'lere embedding üret."""
        while True:
            try:
                await asyncio.sleep(600)
                from core.memory import store
                await store.embed_pending(limit=30)
            except Exception:
                pass

    async def _monthly_wa_loop():
        """Her ayın son günü saat 10:00'da aylık WA kampanyasını başlat."""
        import datetime as _dt
        import calendar
        while True:
            now = _dt.datetime.now()
            last_day = calendar.monthrange(now.year, now.month)[1]
            target = now.replace(day=last_day, hour=10, minute=0, second=0, microsecond=0)
            if now >= target:
                # Bu ay zaten geçti — bir sonraki ayın son gününe atla
                if now.month == 12:
                    next_year, next_month = now.year + 1, 1
                else:
                    next_year, next_month = now.year, now.month + 1
                last_day_next = calendar.monthrange(next_year, next_month)[1]
                target = target.replace(year=next_year, month=next_month, day=last_day_next)
            wait_secs = (target - now).total_seconds()
            logger.info(f"Aylık WA kampanyası: {target.strftime('%Y-%m-%d %H:%M')} tarihinde çalışacak ({wait_secs/3600:.1f}h)")
            await asyncio.sleep(wait_secs)
            try:
                from core.message_bus import Message, MessageType, AgentName
                await bus.send(Message(
                    sender=AgentName.SYSTEM,
                    receiver=AgentName.WHATSAPP,
                    type=MessageType.TASK,
                    content="Aylık WhatsApp kampanyası",
                    metadata={"campaign_type": "monthly"},
                ))
                logger.info("Aylık WA kampanyası başlatıldı")
            except Exception as e:
                logger.warning(f"Aylık WA kampanya hatası: {e}")

    async def _weekly_report_loop():
        """Her Pazartesi sabahı 08:00'de haftalık rapor gönder."""
        import datetime as _dt
        while True:
            now = _dt.datetime.now()
            # Bir sonraki Pazartesi 08:00'i hesapla
            days_ahead = (7 - now.weekday()) % 7  # 0=Pazartesi
            if days_ahead == 0 and now.hour >= 8:
                days_ahead = 7
            next_monday = now.replace(hour=8, minute=0, second=0, microsecond=0) + _dt.timedelta(days=days_ahead)
            wait_secs = (next_monday - now).total_seconds()
            await asyncio.sleep(wait_secs)
            try:
                from core.weekly_report import generate as gen_report
                report_text = gen_report(days=7)
                bot = get_bot()
                if bot:
                    await bot.send(report_text)
                logger.info("Haftalik rapor gonderildi")
            except Exception as e:
                logger.warning(f"Haftalik rapor hatasi: {e}")

    tasks.append(_embed_loop())
    tasks.append(_weekly_report_loop())
    tasks.append(_monthly_wa_loop())
    tasks.append(asyncio.create_task(tracking_start(port=tracking_port)))

    async def _health_monitor():
        """Agent'ları izle, 10 dakika sessiz kalırsa Telegram'a uyarı gönder."""
        import datetime as _dt
        alerted: set[str] = set()
        while True:
            await asyncio.sleep(120)
            try:
                from agents.base import _AGENT_REGISTRY
                now = _dt.datetime.now()
                for name, agent in _AGENT_REGISTRY.items():
                    diff = (now - agent.last_heartbeat).total_seconds()
                    if diff > 600 and name not in alerted:
                        alerted.add(name)
                        _bot = get_bot()
                        if _bot:
                            await _bot.send(
                                f"⚠️ <b>Agent Uyarısı</b>\n"
                                f"<b>{name}</b> {int(diff//60)} dakikadır sessiz!\n"
                                f"Sistem çalışıyor ama bu agent yanıt vermiyor."
                            )
                    elif diff < 300 and name in alerted:
                        alerted.discard(name)
            except Exception:
                pass

    tasks.append(_health_monitor())

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Sistem kapatiliyor...")
        for a in agents:
            a.stop()


if __name__ == "__main__":
    asyncio.run(main())
