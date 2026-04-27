"""
Bütçe Kontrolcüsü — her API çağrısını izler, limiti aşınca sistemi durdurur.
Gemini Flash: ~$0.075/1M input token, ~$0.30/1M output token (ücretsiz tier: 15 RPM, 1M TPD)
"""
import json
import os
from pathlib import Path
from datetime import datetime, date
from loguru import logger

BUDGET_FILE = Path(__file__).parent.parent / "memory" / "budget.json"

# Günlük limitleri — ücretsiz tier için token limitleri
DAILY_TOKEN_LIMIT = 5_000_000  # Tüm providerların toplamı (Groq+Cerebras+Gemini+...)
HOURLY_TOKEN_LIMIT = 300_000   # Aşırı harcamayı önle


class BudgetController:
    def __init__(self):
        self._data = self._load()
        self._today = str(date.today())
        self._ensure_today()

    def _load(self) -> dict:
        if BUDGET_FILE.exists():
            try:
                return json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save(self):
        tmp = BUDGET_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, BUDGET_FILE)

    def _ensure_today(self):
        if self._today not in self._data:
            self._data[self._today] = {
                "tokens_used": 0,
                "requests": 0,
                "by_agent": {},
                "hourly": {},
                "blocked": False,
            }
            self._save()

    def _current_hour(self) -> str:
        return datetime.now().strftime("%H")

    def record(self, tokens: int, agent: str = "unknown"):
        self._today = str(date.today())
        self._ensure_today()
        day = self._data[self._today]

        day["tokens_used"] += tokens
        day["requests"] += 1
        day["by_agent"][agent] = day["by_agent"].get(agent, 0) + tokens

        hour = self._current_hour()
        day["hourly"][hour] = day["hourly"].get(hour, 0) + tokens

        self._save()
        self._check_limits(tokens, agent)

    def _check_limits(self, _tokens: int, agent: str):
        day = self._data[self._today]
        used = day["tokens_used"]
        hour_used = day["hourly"].get(self._current_hour(), 0)

        if used >= DAILY_TOKEN_LIMIT:
            day["blocked"] = True
            self._save()
            logger.error(f"BÜTÇE: Günlük limit aşıldı! {used:,}/{DAILY_TOKEN_LIMIT:,} token. Sistem durduruldu.")
        elif used >= DAILY_TOKEN_LIMIT * 0.8:
            logger.warning(f"BÜTÇE UYARI: Günlük limitin %80'i kullanıldı ({used:,}/{DAILY_TOKEN_LIMIT:,})")
        elif hour_used >= HOURLY_TOKEN_LIMIT:
            logger.warning(f"BÜTÇE: Saatlik limit aşıldı ({hour_used:,} token). Agent: {agent}")

    def is_blocked(self) -> bool:
        self._today = str(date.today())
        self._ensure_today()
        return self._data[self._today].get("blocked", False)

    def daily_usage(self) -> dict:
        self._today = str(date.today())
        self._ensure_today()
        return self._data[self._today]

    def report(self) -> str:
        day = self.daily_usage()
        used = day["tokens_used"]
        pct = (used / DAILY_TOKEN_LIMIT) * 100
        by_agent = "\n".join(f"  • {a}: {t:,} token" for a, t in sorted(day["by_agent"].items(), key=lambda x: -x[1]))
        status = "[BLOKE]" if day["blocked"] else ("[DIKKAT]" if pct > 80 else "[Normal]")
        return (
            f"Butce Raporu [{self._today}]\n"
            f"Durum: {status}\n"
            f"Kullanım: {used:,} / {DAILY_TOKEN_LIMIT:,} token ({pct:.1f}%)\n"
            f"İstek sayısı: {day['requests']}\n"
            f"Agent harcamaları:\n{by_agent or '  Henüz veri yok'}"
        )

    def reset_daily(self):
        self._data[self._today] = {
            "tokens_used": 0, "requests": 0,
            "by_agent": {}, "hourly": {}, "blocked": False,
        }
        self._save()
        logger.info("Bütçe sıfırlandı.")


budget = BudgetController()
