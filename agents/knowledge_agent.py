"""
KnowledgeAgent — sistemin öğrenen beyni.

Görevleri:
1. Başlangıçta sektör KB'yi LLM ile tohumlar (her sektör için 1 kez)
2. 6 saatte bir haftalık yansıma yazar
3. Telegram komutlarını işler: /bilgi, /ogret, /pattern, /haftalik
"""
import asyncio
import datetime as _dt
from loguru import logger
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message, bus
from core.sector_kb import get_kb, SEED_SECTORS

SYSTEM = """You are the knowledge and learning specialist of Bostok.dev.
You manage sector knowledge, analyze successful/failed patterns,
and provide accurate context to other agents. Keep answers short, clear and actionable."""


class KnowledgeAgent(BaseAgent):
    name = AgentName.KNOWLEDGE
    system_prompt = SYSTEM
    max_tokens = 400

    def __init__(self):
        super().__init__()
        self._reflection_interval = 6 * 3600  # 6 saat
        self._seed_done = False

    async def loop(self):
        # Tohumlama — sadece bir kez, startup'ta
        if not self._seed_done:
            await self._seed_all()
            self._seed_done = True

        # Mesajları işle
        msg = await self.receive(timeout=1.0)
        if msg:
            await self._handle(msg)
            return

        # Periyodik yansıma — 6 saatte bir (30s parçalarda uyur → graceful shutdown)
        slept = 0
        while slept < self._reflection_interval:
            if not self.running:
                return
            chunk = min(30, self._reflection_interval - slept)
            await asyncio.sleep(chunk)
            self.last_heartbeat = _dt.datetime.now()
            slept += chunk
        await self._periodic_reflection()

    # ── Mesaj işleme ──────────────────────────────────────────────

    async def _handle(self, msg: Message):
        meta = msg.metadata or {}
        cmd = meta.get("cmd", "")

        if cmd == "bilgi":
            sector = msg.content.strip()
            reply = get_kb().sector_info(sector)
            await self._notify(reply)

        elif cmd == "ogret":
            # content: "sektör|bilgi metni"
            parts = msg.content.split("|", 1)
            if len(parts) == 2:
                get_kb().add_knowledge(parts[0].strip(), parts[1].strip())
                self.save_observation(f"Kullanıcı bilgi ekledi: {parts[0]} — {parts[1][:80]}", 8.0)
                reply = f"✅ Bilgi eklendi: <b>{parts[0].strip()}</b>\n{parts[1].strip()[:150]}"
            else:
                reply = "Format: <code>/ogret restoran|Türk restoranlar WhatsApp'ı tercih eder</code>"
            await self._notify(reply)

        elif cmd == "pattern":
            location = msg.content.strip()
            reply = get_kb().get_summary(location=location)
            await self._notify(reply)

        elif cmd == "haftalik":
            reply = await self._weekly_reflection()
            await self._notify(reply)

    # ── Tohumlama ──────────────────────────────────────────────────

    async def _seed_all(self):
        """Henüz tohumlanmamış sektörleri LLM ile doldur."""
        kb = get_kb()
        pending = [s for s in SEED_SECTORS if kb.needs_seeding(s)]
        if not pending:
            logger.info("KnowledgeAgent: tüm sektörler zaten tohumlanmış")
            return

        logger.info(f"KnowledgeAgent: {len(pending)} sektör tohumlanıyor...")
        for sector in pending:
            try:
                context = await self.ask(
                    f"Write a 5-point summary for selling websites to small/medium businesses "
                    f"in the '{sector}' sector:\n"
                    f"1) Who makes the decision (title/role)\n"
                    f"2) Top 2 pain points (what they lose without a website or with a bad one)\n"
                    f"3) What they expect from a website (concrete features)\n"
                    f"4) Most effective message tone (e.g. 'formal', 'friendly', 'ROI-focused')\n"
                    f"5) 2 phrases or approaches to avoid\n"
                    f"Bullet points only, max 100 words."
                )
                if context and len(context.strip()) > 40:
                    kb.mark_seeded(sector, context.strip())
                    logger.info(f"KnowledgeAgent: '{sector}' tohumlandı")
                self.last_heartbeat = _dt.datetime.now()
                await asyncio.sleep(3)
            except Exception as e:
                logger.debug(f"Seed hata [{sector}]: {e}")

        logger.info("KnowledgeAgent: tohumlama tamamlandı")

    # ── Yansıma ────────────────────────────────────────────────────

    async def _periodic_reflection(self):
        """Öğrenilenleri özetleyip hafızaya yaz."""
        kb = get_kb()
        summary = kb.get_summary()
        if "0 pozitif" in summary and "0 negatif" in summary:
            return  # Henüz veri yok

        try:
            reflection = await self.ask(
                f"Lessons learned from the B2B website sales campaign so far:\n{summary}\n\n"
                f"Summarize in 2-3 sentences and give the single most important concrete recommendation."
            )
            self.save_observation(f"Haftalık yansıma: {reflection[:300]}", importance=9.0)
            logger.info("KnowledgeAgent: periyodik yansıma tamamlandı")
        except Exception as e:
            logger.debug(f"Yansıma hata: {e}")

    async def _weekly_reflection(self) -> str:
        kb = get_kb()
        summary = kb.get_summary()
        try:
            analysis = await self.ask(
                f"Campaign data:\n{summary}\n\n"
                f"3-sentence summary + 1 concrete recommendation."
            )
            return f"{summary}\n\n💡 <b>Analiz:</b>\n{analysis}"
        except Exception:
            return summary

    async def _notify(self, content: str):
        await bus.send(Message(
            sender=AgentName.KNOWLEDGE,
            receiver=AgentName.SYSTEM,
            type=MessageType.USER_NOTIFY,
            content=content,
        ))
