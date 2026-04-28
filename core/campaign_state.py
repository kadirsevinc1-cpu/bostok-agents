"""Kampanya tüketim takibi — tüm leadleri işlenmiş sektör/şehir kombolarını kalıcı olarak izler."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

_STATE_FILE = Path("memory/campaign_exhausted.json")
_REVISIT_DAYS = 90  # 90 gün sonra tekrar dene (yeni işletmeler açılmış olabilir)


def _load() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(data: dict):
    _STATE_FILE.parent.mkdir(exist_ok=True)
    tmp = _STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, _STATE_FILE)


def _key(sector: str, location: str) -> str:
    return f"{sector.lower().strip()}|{location.lower().strip()}"


def is_exhausted(sector: str, location: str) -> bool:
    """Bu sektör/şehir için tüm leadler işlendi mi? 90 gün geçmeden tekrar bakma."""
    data = _load()
    k = _key(sector, location)
    ts_str = data.get(k)
    if not ts_str:
        return False
    try:
        exhausted_at = datetime.fromisoformat(ts_str)
        if datetime.now() - exhausted_at < timedelta(days=_REVISIT_DAYS):
            return True
        # 90 gün geçti — temizle, yeniden dene
        del data[k]
        _save(data)
    except Exception:
        pass
    return False


def mark_exhausted(sector: str, location: str):
    """Sektör/şehir tükendi — 90 gün boyunca atlanacak."""
    data = _load()
    k = _key(sector, location)
    data[k] = datetime.now().isoformat()
    _save(data)
    logger.info(f"Kampanya tükendi, 90 gün atlanacak: {sector}/{location}")


def exhausted_count() -> int:
    data = _load()
    active = sum(
        1 for ts in data.values()
        if datetime.now() - datetime.fromisoformat(ts) < timedelta(days=_REVISIT_DAYS)
    )
    return active


def reset(sector: str = "", location: str = ""):
    """Belirli veya tüm tükenmiş kampanyaları sıfırla."""
    if sector or location:
        data = _load()
        k = _key(sector, location)
        data.pop(k, None)
        _save(data)
        logger.info(f"Kampanya sıfırlandı: {sector}/{location}")
    else:
        _save({})
        logger.info("Tüm kampanya durumları sıfırlandı")
