import asyncio
from loguru import logger
from core.message_bus import bus, AgentName, Message, MessageType


class BaseAgent:
    name: AgentName
    system_prompt: str
    max_tokens: int = 1024

    def __init__(self):
        self.running = False

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
        mem = self.memory_context(user_message)
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

    async def run(self):
        self.running = True
        logger.info(f"{self.name.value} başlatıldı")
        while self.running:
            try:
                await self.loop()
            except Exception as e:
                logger.exception(f"{self.name.value} HATA: {e}")
                await asyncio.sleep(5)

    async def loop(self):
        raise NotImplementedError

    def stop(self):
        self.running = False
