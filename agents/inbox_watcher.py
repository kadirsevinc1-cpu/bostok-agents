"""InboxWatcher — Gmail inbox'ı 5 dakikada bir kontrol eder, bizim outreach maillerimize gelen yanıtları Telegram'a bildirir."""
import asyncio
import datetime as _dt
from loguru import logger
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message, bus


DRAFTS_FILE = __import__("pathlib").Path("memory/drafts.json")
DRAFT_SIGNATURE = "\n\nSaygılar,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev"


async def _generate_draft(body: str, from_name: str, lead_name: str,
                           sector: str, location: str, lang: str) -> str:
    """Soru içerikli yanıt için LLM ile taslak üret."""
    from core.llm_router import router
    from core.user_profile import get_context as profile_ctx

    lang_names = {"tr": "Türkçe", "en": "İngilizce", "de": "Almanca",
                  "nl": "Flemenkçe", "fr": "Fransızca"}
    lang_name = lang_names.get(lang, lang)
    name = lead_name or from_name or "müşteri"

    prompt = (
        f"{profile_ctx('inbox')}\n\n"
        f"Müşteri sorusu ({lang_name}):\n{body[:600]}\n\n"
        f"Müşteri: {name} — {sector}/{location}\n\n"
        f"Bostok.dev adına {lang_name} dilinde kısa, profesyonel yanıt yaz. "
        f"Max 80 kelime. İmza YAZMA. Sadece mail metni."
    )
    try:
        result = await router.chat(
            [{"role": "user", "content": prompt}], max_tokens=300
        )
        return result.strip() if result else ""
    except Exception as e:
        logger.warning(f"Taslak uretme hatasi: {e}")
        return ""


def _save_draft(reply_id: str, draft_text: str) -> None:
    import json as _json
    import os as _os
    data: dict = {}
    if DRAFTS_FILE.exists():
        try:
            data = _json.loads(DRAFTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    data[reply_id] = {
        "draft": draft_text,
        "created_at": __import__("datetime").datetime.now().isoformat(),
    }
    DRAFTS_FILE.parent.mkdir(exist_ok=True)
    tmp = DRAFTS_FILE.with_suffix(".tmp")
    tmp.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _os.replace(tmp, DRAFTS_FILE)


class InboxWatcherAgent(BaseAgent):
    name = AgentName.INBOX_WATCHER
    system_prompt = "Inbox takip agent"
    max_tokens = 100

    async def loop(self):
        from integrations.gmail_reader import get_reader

        reader = get_reader()
        if not reader:
            await asyncio.sleep(60)
            return

        loop = asyncio.get_running_loop()
        try:
            replies = await loop.run_in_executor(None, reader.check_replies)
        except Exception as e:
            logger.error(f"Inbox kontrol hatasi: {e}")
            await asyncio.sleep(300)
            return

        for reply in replies:
            # Bounce / teslimat hatası mı?
            from integrations.gmail import is_bounce, record_bounce
            if is_bounce(reply.from_email):
                # Orijinal alıcıyı sent_info'dan çıkar ve blacklist'e ekle
                sent_info_safe = reply.sent_info or {}
                original_to = sent_info_safe.get("to", "").lower()
                if original_to:
                    record_bounce(original_to)
                    try:
                        from core.lead_state import get_tracker, LeadStage
                        get_tracker().update(original_to, LeadStage.BOUNCED, f"Bounce from: {reply.from_email}")
                    except Exception:
                        pass
                    try:
                        from core.performance_tracker import record_bounce as perf_bounce
                        si = reply.sent_info or {}
                        perf_bounce(si.get("sector", ""), si.get("location", ""))
                    except Exception:
                        pass
                logger.info(f"Bounce tespit edildi, blackliste eklendi: {original_to} (gonden: {reply.from_email})")
                continue

            sent = reply.sent_info or {}
            sector = sent.get("sector", "")
            location = sent.get("location", "")
            lead_name = sent.get("name", "")

            # Niyeti tespit et (0 token)
            from core.skills.reply_analyzer import analyze_reply
            analysis = analyze_reply(reply.body, reply.subject)
            intent_emoji = {
                "ready":       "🔥",
                "meeting":     "📅",
                "interested":  "✨",
                "question":    "❓",
                "negative":    "👎",
                "unsubscribe": "🚫",
                "spam":        "🗑️",
                "unknown":     "🤷",
            }.get(analysis.intent.value, "📧")

            if analysis.intent.value == "spam":
                logger.info(f"Spam yanit atlanıyor: {reply.from_email}")
                continue

            # Lead state güncelle
            try:
                from core.lead_state import get_tracker, LeadStage
                tracker = get_tracker()
                if analysis.intent.value == "unsubscribe":
                    tracker.update(reply.from_email, LeadStage.UNSUBSCRIBED, reply.subject[:80])
                else:
                    tracker.update(reply.from_email, LeadStage.REPLIED,
                                   f"{analysis.intent.value}: {reply.subject[:60]}")
            except Exception:
                pass

            # Performans takibi — yanıt kaydı
            try:
                from core.performance_tracker import record_reply as perf_reply
                perf_reply(sector, location)
            except Exception:
                pass

            # A/B takibi — hangi konu yanıt aldı
            try:
                from core.ab_tracker import record_reply as ab_reply
                ab_reply(reply.matched_message_id)
            except Exception:
                pass

            # KB'ye pattern kaydet
            try:
                from core.sector_kb import get_kb
                lang = reply.sent_info.get("lang", "tr")
                positive_intents = {"ready", "meeting", "interested"}
                negative_intents = {"negative", "unsubscribe"}
                if analysis.intent.value in positive_intents:
                    desc = (f"{sector}/{location}: '{analysis.summary[:100]}' — "
                            f"niyet={analysis.intent.value}")
                    get_kb().add_pattern("positive", sector, location, lang, desc)
                elif analysis.intent.value in negative_intents:
                    desc = (f"{sector}/{location}: '{analysis.summary[:100]}' — "
                            f"niyet={analysis.intent.value}")
                    get_kb().add_pattern("negative", sector, location, lang, desc)
            except Exception:
                pass

            if analysis.intent.value == "unsubscribe":
                logger.info(f"Abonelik iptali: {reply.from_email}")

            # Soru niyetinde otomatik taslak üret
            draft_hint = ""
            if analysis.intent.value == "question":
                draft_text = await _generate_draft(
                    reply.body, reply.from_name, lead_name, sector, location,
                    sent.get("lang", "tr"),
                )
                if draft_text:
                    _save_draft(reply.reply_id, draft_text)
                    draft_hint = (
                        f"\n\n💬 <b>Otomatik Taslak:</b>\n<i>{draft_text[:300]}</i>"
                        f"\n\n✅ Göndermek için: <code>onayla {reply.reply_id}</code>"
                        f"\n✏️ Düzenlemek için: <code>yanit {reply.reply_id} kendi mesajın</code>"
                    )

            # Başarılı pattern'ı kristalleştir
            if analysis.intent.value in ("ready", "meeting", "interested"):
                try:
                    from core.skills.skill_crystallizer import record_success
                    record_success(
                        sector=sector,
                        location=location,
                        lang=sent.get("lang", "tr"),
                        intent=analysis.intent.value,
                        has_website=bool(sent.get("has_website", False)),
                        subject=sent.get("subject", ""),
                    )
                except Exception:
                    pass

            # Yüksek niyet → otomatik teklif gönder
            proposal_hint = ""
            if analysis.intent.value in ("ready", "meeting", "interested"):
                try:
                    from core.skills.proposal_writer import write_proposal
                    from integrations.gmail import get_gmail
                    lang = sent.get("lang", "tr")
                    has_website = bool(sent.get("has_website", False))
                    biz_name = lead_name or reply.from_name or reply.from_email.split("@")[0]
                    prop_subject, prop_body = await write_proposal(
                        lead_name=biz_name,
                        sector=sector,
                        location=location,
                        has_website=has_website,
                        lang=lang,
                        reply_body=reply.body,
                    )
                    if prop_body:
                        gmail = get_gmail()
                        if gmail and gmail.can_send():
                            sent_ok = await gmail.send_reply(
                                reply.from_email,
                                prop_subject,
                                prop_body,
                                in_reply_to=reply.matched_message_id,
                            )
                            if sent_ok:
                                proposal_hint = (
                                    f"\n\n📨 <b>Teklif otomatik gönderildi!</b>\n"
                                    f"<b>Konu:</b> {prop_subject}\n"
                                    f"<i>{prop_body[:250]}...</i>"
                                )
                                try:
                                    from core.lead_state import get_tracker, LeadStage
                                    get_tracker().update(reply.from_email, LeadStage.PROPOSAL_SENT,
                                                         f"Teklif: {prop_subject[:80]}")
                                except Exception:
                                    pass
                            else:
                                proposal_hint = "\n\n⚠️ Teklif oluşturuldu ama gönderilemedi (limit?)"
                        else:
                            proposal_hint = "\n\n⚠️ Teklif oluşturuldu ama mail limiti doldu"
                    else:
                        proposal_hint = "\n\n⚠️ Teklif oluşturulamadı"
                except Exception as _pe:
                    logger.error(f"Otomatik teklif hatasi: {_pe}")
                    proposal_hint = f"\n\n⚠️ Teklif hatası: {_pe}"

            from config import settings as _cfg
            meeting_line = ""
            if analysis.intent.value == "meeting" and _cfg.calendly_url:
                meeting_line = f"\n\n📅 <b>Toplanti istiyor!</b> Takvim linki: {_cfg.calendly_url}"

            notify = (
                f"{intent_emoji} <b>Yeni Yanit!</b> [ID: {reply.reply_id}]\n"
                f"<b>Niyet:</b> {analysis.summary}\n"
                f"<b>Oneri:</b> {analysis.suggested_action}\n\n"
                f"<b>Kimden:</b> {reply.from_name} &lt;{reply.from_email}&gt;\n"
                f"<b>Konu:</b> {reply.subject}\n"
            )
            if lead_name:
                notify += f"<b>İşletme:</b> {lead_name}\n"
            if sector or location:
                notify += f"<b>Kampanya:</b> {sector} — {location}\n"
            notify += f"\n<b>Mesaj:</b>\n{reply.body[:400]}"
            if len(reply.body) > 400:
                notify += "..."
            notify += meeting_line
            notify += draft_hint
            notify += proposal_hint
            if not draft_hint and not proposal_hint:
                notify += f"\n\n<i>Yanitlamak icin:\nyanit {reply.reply_id} Merhaba, teklif icin...</i>"

            await bus.send(Message(
                sender=AgentName.INBOX_WATCHER,
                receiver=AgentName.SYSTEM,
                type=MessageType.USER_NOTIFY,
                content=notify,
            ))
            logger.info(f"Yanit bildirimi gonderildi: {reply.from_email} [{reply.reply_id}]")

        for _ in range(10):
            if not self.running:
                return
            self.last_heartbeat = _dt.datetime.now()
            await asyncio.sleep(30)
