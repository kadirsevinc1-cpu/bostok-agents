import json
import math
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from loguru import logger

MEMORY_DIR = Path(__file__).parent.parent / "memory"
MEMORY_DIR.mkdir(exist_ok=True)
STREAM_FILE = MEMORY_DIR / "stream.json"
MAX_STREAM  = 600


@dataclass
class Memory:
    content:       str
    agent:         str
    type:          str
    importance:    float
    created_at:    float
    last_accessed: float
    access_count:  int = 0
    id:            str = field(default_factory=lambda: uuid.uuid4().hex[:8])


class MemoryStore:
    def __init__(self):
        self._memories: list[Memory] = []
        self._reflect_counters: dict[str, int] = {}
        self._load()

    def add(self, content: str, agent: str, type: str = "observation", importance: float = 5.0) -> Memory:
        m = Memory(
            content=content[:400], agent=agent, type=type,
            importance=float(importance),
            created_at=time.time(), last_accessed=time.time(),
        )
        self._memories.append(m)
        self._reflect_counters[agent] = self._reflect_counters.get(agent, 0) + 1
        self._save()
        return m

    def retrieve(self, query: str, agent: str, n: int = 10) -> list[Memory]:
        now = time.time()
        pool = [m for m in self._memories if m.agent == agent]
        query_words = set(query.lower().split()) if query else set()

        def score(m: Memory) -> float:
            hours_ago  = (now - m.last_accessed) / 3600
            recency    = math.pow(0.995, hours_ago * 60)
            importance = m.importance / 10.0
            relevance  = len(query_words & set(m.content.lower().split())) / max(len(query_words), 1) if query_words else 0.4
            bonus      = 1.4 if m.type == "reflection" else (1.2 if m.type == "plan" else 1.0)
            return recency * importance * (0.3 + relevance * 0.7) * bonus

        top = sorted(pool, key=score, reverse=True)[:n]
        for m in top:
            m.last_accessed = now
            m.access_count += 1
        return top

    def get_recent(self, agent: str, n: int = 20) -> list[Memory]:
        pool = [m for m in self._memories if m.agent == agent]
        return sorted(pool, key=lambda m: m.created_at, reverse=True)[:n]

    def should_reflect(self, agent: str) -> bool:
        return self._reflect_counters.get(agent, 0) >= 8

    def reset_reflect_counter(self, agent: str):
        self._reflect_counters[agent] = 0

    def _save(self):
        try:
            STREAM_FILE.write_text(
                json.dumps([asdict(m) for m in self._memories[-MAX_STREAM:]], ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"MemoryStore save error: {e}")

    def _load(self):
        if not STREAM_FILE.exists():
            return
        try:
            data = json.loads(STREAM_FILE.read_text(encoding="utf-8"))
            self._memories = [Memory(**d) for d in data]
            logger.info(f"MemoryStore: {len(self._memories)} kayıt yüklendi")
        except Exception as e:
            logger.warning(f"MemoryStore load error: {e}")


store = MemoryStore()


def get_context(agent: str, query: str = "", n: int = 8) -> str:
    mems = store.retrieve(query or "gorev proje musteri", agent, n=n)
    if not mems:
        return ""
    lines = []
    for m in mems:
        ts = datetime.fromtimestamp(m.created_at).strftime("%m/%d %H:%M")
        lines.append(f"[{ts}][{m.type}] {m.content[:180]}")
    return "\n".join(lines)


def _path(name: str) -> Path:
    return MEMORY_DIR / f"{name}.json"


def load(name: str, default=None):
    p = _path(name)
    if not p.exists():
        return default if default is not None else {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Memory load error ({name}): {e}")
        return default if default is not None else {}


def save(name: str, data):
    try:
        _path(name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Memory save error ({name}): {e}")


def add_task(task: str, result: str, agent: str = "Developer"):
    importance = 7.5 if len(result) > 150 else 5.0
    store.add(f"Gorev: {task}\nSonuc: {result[:300]}", agent, "observation", importance)
    history = load("tasks_done", default=[])
    history.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "agent": agent,
        "task": task[:200],
        "result": result[:500],
    })
    save("tasks_done", history[-100:])


def get_task_summary() -> str:
    history = load("tasks_done", default=[])
    if not history:
        return "Henüz tamamlanmış görev yok."
    lines = [f"[{t['date']}] {t['agent']}: {t['task'][:60]}" for t in history[-5:]]
    return "Son tamamlanan görevler:\n" + "\n".join(lines)


def save_clients(clients: list):
    existing = load("clients", default=[])
    existing.extend(clients)
    save("clients", existing[-500:])


def get_clients() -> list:
    return load("clients", default=[])
