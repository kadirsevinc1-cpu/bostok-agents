"""Lead lifecycle state tracker — her lead'in hangi aşamada olduğunu takip eder."""
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from loguru import logger

STATE_FILE = Path("memory/lead_states.json")


class LeadStage(str, Enum):
    NEW          = "new"
    CONTACTED    = "contacted"       # İlk mail gönderildi
    FOLLOWED_UP  = "followed_up"     # 1. takip gönderildi
    FOLLOWED_UP2 = "followed_up2"    # 2. takip gönderildi
    REPLIED      = "replied"         # Yanıt geldi
    BOUNCED      = "bounced"         # Mail bounce etti
    UNSUBSCRIBED = "unsubscribed"    # Abonelik iptali
    CLOSED_WON   = "closed_won"      # Müşteri oldu
    CLOSED_LOST  = "closed_lost"     # Kapandı, olmadı


@dataclass
class LeadEvent:
    ts: str
    type: str
    note: str


@dataclass
class LeadRecord:
    email: str
    name: str
    sector: str
    location: str
    stage: str = LeadStage.NEW
    events: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class LeadStateTracker:
    def __init__(self):
        self._leads: dict[str, LeadRecord] = {}
        self._load()

    def upsert(self, email: str, name: str = "", sector: str = "", location: str = "") -> LeadRecord:
        """Lead yoksa oluştur, varsa güncelleme yapma."""
        key = email.strip().lower()
        if key not in self._leads:
            self._leads[key] = LeadRecord(email=key, name=name, sector=sector, location=location)
            self._save()
        return self._leads[key]

    def update(self, email: str, stage: LeadStage, note: str = ""):
        """Stage'i güncelle, event ekle."""
        key = email.strip().lower()
        if key not in self._leads:
            self._leads[key] = LeadRecord(email=key, name="", sector="", location="")
        rec = self._leads[key]
        old_stage = rec.stage
        rec.stage = stage.value
        rec.updated_at = datetime.now().isoformat()
        rec.events.append(asdict(LeadEvent(
            ts=datetime.now().isoformat(),
            type=stage.value,
            note=note[:200] if note else "",
        )))
        self._save()
        logger.debug(f"Lead state: {key} {old_stage} → {stage.value}")

    def add_event(self, email: str, type: str, note: str = ""):
        """Stage değiştirmeden event ekle."""
        key = email.strip().lower()
        if key not in self._leads:
            return
        rec = self._leads[key]
        rec.events.append(asdict(LeadEvent(
            ts=datetime.now().isoformat(),
            type=type,
            note=note[:200] if note else "",
        )))
        rec.updated_at = datetime.now().isoformat()
        self._save()

    def get(self, email: str) -> LeadRecord | None:
        return self._leads.get(email.strip().lower())

    def get_stage(self, email: str) -> LeadStage | None:
        rec = self.get(email)
        if rec:
            return LeadStage(rec.stage)
        return None

    def get_by_stage(self, stage: LeadStage) -> list[LeadRecord]:
        return [r for r in self._leads.values() if r.stage == stage.value]

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self._leads.values():
            counts[r.stage] = counts.get(r.stage, 0) + 1
        return counts

    def _save(self):
        STATE_FILE.parent.mkdir(exist_ok=True)
        data = {k: asdict(v) for k, v in self._leads.items()}
        tmp = STATE_FILE.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, STATE_FILE)
        except Exception as e:
            logger.warning(f"LeadStateTracker save error: {e}")

    def _load(self):
        if not STATE_FILE.exists():
            return
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            for k, v in data.items():
                self._leads[k] = LeadRecord(**v)
            logger.info(f"LeadStateTracker: {len(self._leads)} lead yüklendi")
        except Exception as e:
            logger.warning(f"LeadStateTracker load error: {e}")


_tracker = LeadStateTracker()


def get_tracker() -> LeadStateTracker:
    return _tracker
