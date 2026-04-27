"""
KnowledgeAgent — sistemin öğrenen beyni.

Görevleri:
1. Başlangıçta sektör KB'yi LLM ile tohumlar (her sektör için 1 kez)
2. 6 saatte bir haftalık yansıma yazar
3. Telegram komutlarını işler: /bilgi, /ogret, /pattern, /haftalik
"""
import asyncio
from loguru import logger
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message, bus
from core.sector_kb import get_kb, SEED_SECTORS

SYSTEM = """Sen Bostok.dev'in bilgi ve öğrenme uzmanısın.
Sektör bilgisini yönetir, başarılı/başarısız pattern'leri analiz eder,
diğer agent'lara doğru bağlamı sağlarsın. Yanıtların kısa, net ve uygulanabilir olur."""


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
                    f"'{sector}' sektöründeki Türkiye'deki küçük/orta işletmelere "
                    f"web sitesi satışı için 5 maddelik özet yaz:\n"
                    f"1) Kim karar verir (unvan/rol)\n"
                    f"2) En büyük 2 ağrı noktası (web sitesi yok/kötü olunca ne kaybediyorlar)\n"
                    f"3) Web sitesinden ne beklerler (somut özellikler)\n"
                    f"4) En etkili mesaj tonu (örnek: 'resmi', 'samimi', 'ROI odaklı')\n"
                    f"5) Kaçınılması gereken 2 ifade veya yaklaşım\n"
                    f"Sadece maddeler, max 100 kelime."
                )
                if context and len(context.strip()) > 40:
                    kb.mark_seeded(sector, context.strip())
                    logger.info(f"KnowledgeAgent: '{sector}' tohumlandı")
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
                f"B2B web sitesi satış kampanyasından bugüne kadar öğrenilenler:\n{summary}\n\n"
                f"Bunları 2-3 cümleyle özetle ve en önemli 1 somut öneri ver."
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
                f"Kampanya verileri:\n{summary}\n\n"
                f"3 cümle özet + 1 somut öneri."
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
