"""FollowupAgent — yanıt gelmeyen leadlere 7. ve 14. günde otomatik takip maili atar."""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from loguru import logger
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message, bus

SENT_IDS_FILE = Path("memory/sent_message_ids.json")
INBOX_FILE    = Path("memory/inbox_emails.json")
FOLLOWUP_LOG  = Path("memory/followup_log.json")

SYSTEM = """Sen Bostok.dev ajansının takip uzmanısın.
Görevin: Yanıt gelmemiş outreach maillerine kısa, samimi, baskısız takip maili yazmak.
Asla ısrarcı veya agresif olma."""


class FollowupAgent(BaseAgent):
    name = AgentName.FOLLOWUP
    system_prompt = SYSTEM
    max_tokens = 600

    async def loop(self):
        await self._check_and_send()
        await asyncio.sleep(86400)  # 24 saatte bir kontrol

    async def _check_and_send(self):
        sent_ids = self._load_json(SENT_IDS_FILE)
        if not sent_ids:
            return

        replied_emails = self._get_replied_emails()
        followup_log = self._load_json(FOLLOWUP_LOG)

        from integrations.gmail import get_gmail
        gmail = get_gmail()
        if not gmail or not gmail.can_send():
            logger.info("FollowupAgent: Gmail yok veya limit doldu")
            return

        now = datetime.now()
        sent_count = 0

        for msg_id, info in sent_ids.items():
            to = info.get("to", "").lower()
            if not to:
                continue
            if to in replied_emails:
                continue  # Yanıt vermişse dokunma

            sent_at_str = info.get("sent_at", "")
            try:
                sent_at = datetime.fromisoformat(sent_at_str)
            except Exception:
                continue

            days_since = (now - sent_at).days
            log_entry = followup_log.get(to, {})

            if days_since >= 7 and not log_entry.get("f1_sent"):
                if not gmail.can_send():
                    break
                ok = await self._send_followup(gmail, to, info, msg_id, stage=1)
                if ok:
                    log_entry["f1_sent"] = now.isoformat()
                    followup_log[to] = log_entry
                    self._save_json(FOLLOWUP_LOG, followup_log)
                    sent_count += 1
                    await self._notify(to, info, stage=1)
                    await asyncio.sleep(10)

            elif days_since >= 14 and log_entry.get("f1_sent") and not log_entry.get("f2_sent"):
                try:
                    f1_date = datetime.fromisoformat(log_entry["f1_sent"])
                except Exception:
                    continue
                if (now - f1_date).days < 7:
                    continue  # F1'den bu yana henüz 7 gün geçmemiş
                if not gmail.can_send():
                    break
                ok = await self._send_followup(gmail, to, info, msg_id, stage=2)
                if ok:
                    log_entry["f2_sent"] = now.isoformat()
                    followup_log[to] = log_entry
                    self._save_json(FOLLOWUP_LOG, followup_log)
                    sent_count += 1
                    await self._notify(to, info, stage=2)
                    await asyncio.sleep(10)

        if sent_count:
            logger.info(f"FollowupAgent: {sent_count} follow-up gonderildi")

    async def _send_followup(self, gmail, to: str, info: dict, original_msg_id: str, stage: int) -> bool:
        original_subject = info.get("subject", "Web Site Teklifi")
        subject = original_subject if original_subject.lower().startswith("re:") else f"Re: {original_subject}"
        sector   = info.get("sector", "")
        location = info.get("location", "")
        name     = info.get("name", "")

        if stage == 1:
            prompt = (
                f"Bir {sector} işletmesine ({name}, {location}) 7 gün önce web site teklifi "
                f"gönderdik ama yanıt gelmedi.\n"
                "Kısa, samimi, baskısız takip maili yaz. Max 80 kelime.\n"
                "Ton: 'Sadece takip ediyorum, görme fırsatı buldunuz mu?' tarzında.\n"
                "Sona https://bostok.dev linki ve imza ekle: Kadir Şevinç — Bostok.dev\n"
                "Sadece mail gövdesini yaz, konu satırı yazma."
            )
        else:
            prompt = (
                f"Bir {sector} işletmesine ({name}, {location}) iki haftadır iki mail gönderdik, "
                f"yanıt yok.\n"
                "Kibarca kapanış maili yaz. Max 60 kelime.\n"
                "Ton: 'Son kez yazıyorum, ilgi duymuyorsanız sorun değil, ihtiyaç olursa buradayım.'\n"
                "Sona https://bostok.dev linki ve imza ekle: Kadir Şevinç — Bostok.dev\n"
                "Sadece mail gövdesini yaz, konu satırı yazma."
            )

        try:
            body = await self.ask(prompt)
            if len(body.strip()) < 20:
                return False
            return await gmail.send_reply(to, subject, body, in_reply_to=original_msg_id)
        except Exception as e:
            logger.error(f"Followup mail hata [{to}]: {e}")
            return False

    async def _notify(self, to: str, info: dict, stage: int):
        label = "7. gun" if stage == 1 else "14. gun (kapanis)"
        name     = info.get("name", "")
        sector   = info.get("sector", "")
        location = info.get("location", "")
        await bus.send(Message(
            sender=AgentName.FOLLOWUP,
            receiver=AgentName.SYSTEM,
            type=MessageType.USER_NOTIFY,
            content=f"Follow-up gonderildi: {to} ({label})\n{name} — {sector} / {location}",
        ))

    def _get_replied_emails(self) -> set:
        inbox = self._load_json(INBOX_FILE)
        return {v.get("from_email", "").lower() for v in inbox.values()}

    def _load_json(self, path: Path) -> dict:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_json(self, path: Path, data: dict):
        path.parent.mkdir(exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
