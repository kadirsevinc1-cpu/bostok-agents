import asyncio
import datetime as _dt
from loguru import logger
from core.message_bus import bus, AgentName, Message, MessageType

_AGENT_REGISTRY: dict[str, "BaseAgent"] = {}


class BaseAgent:
    name: AgentName
    system_prompt: str
    max_tokens: int = 1024

    def __init__(self):
        self.running = False
        self.last_heartbeat: _dt.datetime = _dt.datetime.now()
        self.loop_count: int = 0

    def memory_context(self, query: str = "") -> str:
        from core import memory
        return memory.get_context(self.name.value, query=query, n=7)

    def save_observation(self, content: str, importance: float = 5.0):
        from core import memory
        memory.store.add(content, self.name.value, "observation", importance)

    async def think(self, messages: list[dict]) -> str:
        from core.llm_router import router
        return await router.chat(messages, max_tokens=self.max_tokens)

    async def ask(self, user_message: str, context: str = "") -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        from core.memory import aget_context
        mem = await aget_context(self.name.value, query=user_message, n=7)
        if mem:
            messages.append({"role": "user", "content": f"[Geçmiş hafıza]\n{mem}"})
            messages.append({"role": "assistant", "content": "Hafızam hazır."})
        if context:
            messages.append({"role": "user", "content": f"[Bağlam]\n{context}"})
            messages.append({"role": "assistant", "content": "Bağlamı aldım."})
        messages.append({"role": "user", "content": user_message})
        return await self.think(messages)

    async def send(self, to: AgentName, type: MessageType, content: str, metadata: dict = None):
        msg = Message(sender=self.name, receiver=to, type=type, content=content, metadata=metadata or {})
        await bus.send(msg)
        logger.info(f"{self.name.value} → {to.value}: {content[:60]}")

    async def receive(self, timeout: float = None) -> Message | None:
        return await bus.receive(self.name, timeout=timeout)

    async def _notify_crash(self, message: str):
        try:
            from integrations.telegram import get_bot
            bot = get_bot()
            if bot:
                await bot.send(message)
        except Exception:
            pass

    async def run(self):
        self.running = True
        _AGENT_REGISTRY[self.name.value] = self
        logger.info(f"{self.name.value} başlatıldı")
        crash_count = 0
        while self.running:
            try:
                self.last_heartbeat = _dt.datetime.now()
                await self.loop()
                self.loop_count += 1
                crash_count = 0
            except Exception as e:
                crash_count += 1
                logger.exception(f"{self.name.value} HATA ({crash_count}/10): {e}")
                if crash_count >= 10:
                    logger.error(f"{self.name.value} arka arkaya 10 hata, durduruluyor")
                    self.running = False
                    await self._notify_crash(
                        f"🚨 <b>Agent Çöktü!</b>\n"
                        f"<b>Agent:</b> {self.name.value}\n"
                        f"<b>Hata:</b> {str(e)[:300]}\n"
                        f"<b>Durum:</b> Arka arkaya 10 hata — agent durduruldu."
                    )
                    break
                await asyncio.sleep(5)

    async def loop(self):
        raise NotImplementedError

    def stop(self):
        self.running = False
