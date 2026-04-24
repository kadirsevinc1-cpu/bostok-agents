import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Any


class AgentName(str, Enum):
    MANAGER   = "Yönetici"
    MARKETING = "Pazarlama"
    ANALYST   = "Analist"
    QUOTE     = "Teklif"
    CONTENT   = "İçerik"
    DESIGNER  = "Tasarımcı"
    DEVELOPER = "Developer"
    QA        = "QA"
    DEPLOY         = "Deploy"
    INBOX_WATCHER  = "InboxTakip"
    BUDGET    = "Bütçe"
    REPORT    = "Rapor"
    FOLLOWUP  = "Takip"
    SYSTEM    = "Sistem"


class MessageType(str, Enum):
    TASK           = "task"
    RESULT         = "result"
    STATUS         = "status"
    CLIENT_REQUEST = "client_request"
    USER_NOTIFY    = "user_notify"
    BUDGET_ALERT   = "budget_alert"
    APPROVAL       = "approval"


@dataclass
class Message:
    sender:   AgentName
    receiver: AgentName
    type:     MessageType
    content:  str
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.sender.value} → {self.receiver.value}: {self.content[:80]}"


class MessageBus:
    def __init__(self):
        self._queues: dict[AgentName, asyncio.Queue] = {
            name: asyncio.Queue() for name in AgentName
        }
        self._listeners: list[Callable[[Message], Any]] = []

    async def send(self, msg: Message):
        msg.content = ''.join(c for c in msg.content if c.isprintable() or c in '\n\t')
        await self._queues[msg.receiver].put(msg)
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(msg)
                else:
                    listener(msg)
            except Exception:
                pass

    async def receive(self, agent: AgentName, timeout: float = None) -> Message | None:
        try:
            if timeout:
                return await asyncio.wait_for(self._queues[agent].get(), timeout=timeout)
            return await self._queues[agent].get()
        except asyncio.TimeoutError:
            return None

    def add_listener(self, fn: Callable[[Message], Any]):
        self._listeners.append(fn)


bus = MessageBus()
