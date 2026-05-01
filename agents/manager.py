import asyncio
import json as _json
from pathlib import Path as _Path
from loguru import logger
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message

_IDX_FILE = _Path("memory/campaign_idx.json")


def _build_system() -> str:
    from core.user_profile import get_context
    profile_ctx = get_context("manager")
    base = """You are the Manager agent of Bostok.dev web agency.

Bostok.dev: Professional web design and development agency. https://bostok.dev

Your responsibilities:
1. Analyze incoming client requests
2. Send to Analyst for brief preparation
3. Get pricing from Quote agent
4. Manage Content, Designer, Developer, QA, Deploy agents in sequence
5. Perform quality control
6. Notify user when demo is ready
7. Publish once approval is received

Rules:
- Stop the pipeline on budget overrun
- Save every step to memory
- Communicate with clients in Turkish, professionally
- Explain decisions with brief reasoning"""
    return f"{profile_ctx}\n\n{base}" if profile_ctx else base


SYSTEM = _build_system()


class ManagerAgent(BaseAgent):
    name = AgentName.MANAGER
    system_prompt = SYSTEM
    max_tokens = 1500

    def __init__(self):
        super().__init__()
        self._current_site_dir: str = ""
        self._current_project_name: str = ""
        self._marketing_paused: bool = False
        self._mail_limit_hit_today: bool = False
        self._qa_retries: int = 0
        self._qa_max_retries: int = 2

    async def run(self):
        """BaseAgent.run() + arka planda kampanya scheduler başlat."""
        asyncio.create_task(self._campaign_scheduler())
        await super().run()

    async def loop(self):
        msg = await self.receive(timeout=1.0)
        if not msg:
            return
        await self._process(msg)

    # ── Kampanya Scheduler ────────────────────────────────────────

    async def _campaign_scheduler(self):
        """main.py'den taşındı — Manager kampanyaları kendisi yönetir."""
        from core.campaigns import CAMPAIGNS
        from core.campaign_state import is_exhausted
        import datetime as _dt

        await asyncio.sleep(50)  # Tüm agentler başlasın

        campaign_idx = 0
        try:
            campaign_idx = int(_json.loads(_IDX_FILE.read_text(encoding="utf-8"))) if _IDX_FILE.exists() else 0
            logger.info(f"Kampanya scheduler baslatildi — idx={campaign_idx} ({campaign_idx % len(CAMPAIGNS) + 1}/{len(CAMPAIGNS)})")
        except Exception:
            logger.info("Kampanya scheduler baslatildi — idx=0")

        while self.running:
            # Günlük limit sıfırlandı mı kontrol et
            _now = _dt.datetime.utcnow()
            if _now.hour == 0 and self._mail_limit_hit_today:
                self._mail_limit_hit_today = False
                if self._marketing_paused:
                    await self._resume_marketing("Yeni gün — günlük mail limiti sıfırlandı")

            if self._marketing_paused:
                await asyncio.sleep(60)
                continue

            campaign = CAMPAIGNS[campaign_idx % len(CAMPAIGNS)]
            campaign_idx += 1
            total = len(campaign["locations"])

            try:
                _IDX_FILE.parent.mkdir(exist_ok=True)
                _IDX_FILE.write_text(_json.dumps(campaign_idx), encoding="utf-8")
            except Exception:
                pass

            logger.info(
                f"[Manager→Kampanya {campaign_idx}/{len(CAMPAIGNS)}] "
                f"{campaign['sector'].upper()} — {total} lokasyon"
            )

            sent_count = 0
            for loc_idx, location in enumerate(campaign["locations"], 1):
                if not self.running:
                    return
                if self._marketing_paused:
                    break
                if is_exhausted(campaign["sector"], location):
                    logger.debug(f"  [{loc_idx}/{total}] Atlandi (tukendi): {campaign['sector']}/{location}")
                    continue

                logger.info(f"  [{loc_idx}/{total}] Gonderiliyor: {campaign['sector']} — {location}")
                await self.send(
                    AgentName.MARKETING, MessageType.TASK,
                    f"{location}'daki {campaign['sector']} isletmelerine web sitesi teklifi hazirla",
                    {
                        "sector": campaign["sector"],
                        "location": location,
                        "languages": campaign["langs"],
                        "send_emails": True,
                    },
                )
                sent_count += 1
                await asyncio.sleep(10)

            if sent_count > 0:
                logger.info(f"[Manager] {campaign['sector']} — {sent_count} lokasyon gonderildi, 10 dk bekleniyor")
                await asyncio.sleep(600)
            else:
                await asyncio.sleep(2)

    async def _pause_marketing(self, reason: str):
        if not self._marketing_paused:
            self._marketing_paused = True
            await self.send(AgentName.MARKETING, MessageType.PAUSE, reason)
            logger.warning(f"Marketing DURDURULDU: {reason}")

    async def _resume_marketing(self, reason: str):
        if self._marketing_paused:
            self._marketing_paused = False
            await self.send(AgentName.MARKETING, MessageType.RESUME, reason)
            logger.info(f"Marketing DEVAM EDiYOR: {reason}")

    async def _process(self, msg: Message):
        from loguru import logger

        logger.info(f"Yonetici mesaj aldi: {msg.sender.value} -> {msg.content[:80]}")
        self.save_observation(f"Mesaj: [{msg.sender.value}] {msg.content[:200]}", importance=7.0)

        if msg.type == MessageType.CLIENT_REQUEST:
            await self.send(
                AgentName.ANALYST, MessageType.TASK,
                msg.content,
                {"source": msg.sender.value},
            )
            await self.send(
                AgentName.SYSTEM, MessageType.USER_NOTIFY,
                "Talebiniz alındı. Analist brief hazırlıyor, ardından teklif ve içerik oluşturulacak.",
            )

        elif msg.type == MessageType.RESULT:
            result = msg.content

            if msg.sender == AgentName.MARKETING:
                # Sadece gerçek mail gönderimlerini bildir (0 gönderim → sessiz)
                import re as _re
                m = _re.search(r"Gonderilen:\s*(\d+)", result)
                sent_count = int(m.group(1)) if m else 0
                if sent_count > 0:
                    await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                    f"📬 Pazarlama:\n{result}")
                else:
                    logger.debug(f"Marketing sonucu sessizce gecildi (gonderilen=0)")

            elif msg.sender == AgentName.ANALYST:
                project_name = msg.metadata.get("project_name", "")
                if project_name:
                    self._current_project_name = project_name
                meta = {"project_name": self._current_project_name}

                # Konsey toplantısı — 3 uzman paralel oy kullanır (~500 token)
                await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                "Konsey toplantısı başladı, brief değerlendiriliyor...")
                from core.council import hold_meeting
                decision = await hold_meeting(result)
                self.save_observation(f"Konsey: {decision.report()[:200]}", importance=9.0)
                await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY, decision.report())

                if not decision.approved:
                    return  # 2/3 RET — pipeline durduruldu

                await self.send(AgentName.QUOTE, MessageType.TASK, result, meta)
                await self.send(AgentName.CONTENT, MessageType.TASK, result, meta)

            elif msg.sender == AgentName.QUOTE:
                await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                f"Teklif hazir:\n{result}")

            elif msg.sender == AgentName.CONTENT:
                await self.send(AgentName.DESIGNER, MessageType.TASK, result,
                                {"project_name": self._current_project_name})

            elif msg.sender == AgentName.DESIGNER:
                await self.send(AgentName.DEVELOPER, MessageType.TASK, result,
                                {"project_name": self._current_project_name})

            elif msg.sender == AgentName.DEVELOPER:
                # Site dizinini sakla — QA'dan sonra Deploy'a göndereceğiz
                file_path = msg.metadata.get("file_path", "")
                self._current_project_name = msg.metadata.get("project_name", "site")
                from pathlib import Path
                if file_path:
                    self._current_site_dir = str(Path(file_path).parent)
                await self.send(AgentName.QA, MessageType.TASK, result,
                                {"file_path": file_path,
                                 "site_dir": self._current_site_dir,
                                 "project_name": self._current_project_name})

            elif msg.sender == AgentName.QA:
                has_critical = msg.metadata.get("has_critical_errors", False)
                site_dir = msg.metadata.get("site_dir", self._current_site_dir)
                project_name = msg.metadata.get("project_name", self._current_project_name)
                file_path = msg.metadata.get("file_path", "")

                if has_critical:
                    if self._qa_retries < self._qa_max_retries:
                        self._qa_retries += 1
                        logger.info(f"QA kritik hata — otomatik duzeltme denemesi {self._qa_retries}/{self._qa_max_retries}")
                        await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                        f"⚠️ QA {self._qa_retries}. hata buldu, Developer otomatik düzeltiyor...\n\n{result[:300]}")
                        await self.send(
                            AgentName.DEVELOPER, MessageType.TASK,
                            f"QA found these critical errors — fix them all:\n\n{result}",
                            {"revision": True, "site_dir": site_dir,
                             "project_name": project_name, "file_path": file_path},
                        )
                    else:
                        self._qa_retries = 0
                        await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                        f"❌ QA {self._qa_max_retries} denemede düzeltilemedi, deploy durduruldu:\n\n{result[:500]}")
                else:
                    self._qa_retries = 0
                    await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                    f"QA tamamlandi, site yukleniyor...\n\n{result[:300]}")
                    await self.send(
                        AgentName.DEPLOY, MessageType.TASK,
                        result,
                        {"site_dir": site_dir, "project_name": project_name},
                    )

            elif msg.sender == AgentName.DEPLOY:
                # Deploy tamamlandı → kullanıcıya demo linki sun
                url = msg.metadata.get("url", "")
                local = msg.metadata.get("local_path", "")

                if url:
                    notify = (
                        f"Site demo hazir!\n\n"
                        f"Demo linki: {url}\n\n"
                        f"Yayinda kalmasi icin onay verin."
                    )
                else:
                    notify = (
                        f"Netlify deploy yapilamadi.\n"
                        f"Site yerel olarak hazir: {local}\n\n"
                        f"Netlify token'i .env'e ekleyerek otomatik deploy yapilabilir."
                    )
                await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY, notify,
                                {"requires_approval": bool(url)})

        elif msg.type == MessageType.STATUS and msg.metadata.get("note_type") == "revizyon":
            revision = msg.content
            self.save_observation(f"Revize talebi: {revision}", importance=9.0)

            if not self._current_site_dir:
                await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                "⚠️ Aktif proje yok — önce bir site oluşturun.")
                return

            await self.send(
                AgentName.DEVELOPER, MessageType.TASK,
                f"Mevcut siteyi revize et: {revision}",
                {
                    "site_dir": self._current_site_dir,
                    "project_name": self._current_project_name,
                    "revision": True,
                },
            )
            await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                            f"🔧 Revize Developer'a iletildi: <i>{revision[:100]}</i>")

        elif msg.type == MessageType.STATUS and msg.metadata.get("user_note"):
            note_type = msg.metadata.get("note_type", "not")
            note = msg.content
            self.save_observation(f"Kullanici {note_type}: {note}", importance=9.0)
            response = await self.ask(
                f"A '{note_type}' note received from the user: {note}\n"
                "Explain how to incorporate this into the current workflow and take the necessary action."
            )
            await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY, response)

        elif msg.type == MessageType.APPROVAL:
            await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                            "Onay alindi! Site yayinda.")
            self.save_observation("Site yayina alindi", importance=9.0)

        elif msg.type == MessageType.CAMPAIGN_STATUS:
            event = msg.metadata.get("event", "")
            if event == "mail_limit_hit":
                self._mail_limit_hit_today = True
                await self._pause_marketing("Günlük mail limiti doldu")
                await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                                "📭 <b>Günlük mail limiti doldu.</b> Marketing durduruldu, yarın otomatik devam eder.")

        elif msg.type == MessageType.BUDGET_ALERT:
            await self.send(AgentName.SYSTEM, MessageType.USER_NOTIFY,
                            f"Butce Uyarisi: {msg.content}")
