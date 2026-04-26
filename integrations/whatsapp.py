"""Green-API üzerinden WhatsApp mesajı gönderme entegrasyonu.

Kurulum:
1. https://green-api.com üzerinde hesap aç (ücretsiz: 1500 msg/ay)
2. Yeni instance oluştur → telefonu bağla (QR kod ile)
3. .env'e ekle: GREENAPI_INSTANCE_ID ve GREENAPI_API_TOKEN
"""
import re
import aiohttp
from loguru import logger

_BASE = "https://api.green-api.com"
_instance: "WhatsAppClient | None" = None


def _format_phone(raw: str) -> str | None:
    """Ham telefon numarasını WhatsApp chat ID formatına çevir: 905XXXXXXXXX@c.us"""
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    # Türkiye: 10 hane → 90 ekle
    if len(digits) == 10 and digits.startswith("5"):
        digits = "90" + digits
    # Uluslararası formattaysa doğru kabul et
    if len(digits) < 10 or len(digits) > 15:
        return None
    return f"{digits}@c.us"


class WhatsAppClient:
    # Ücretsiz plan: sadece 3 farklı numaraya mesaj gönderilebilir.
    # Ücretli plana geçince FREE_TIER_CONTACT_LIMIT'i kaldır veya yükselt.
    FREE_TIER_CONTACT_LIMIT = 3

    def __init__(self, instance_id: str, token: str):
        self._id    = instance_id
        self._token = token
        self._sent_today   = 0
        self._daily_limit  = 100
        self._sent_numbers: set[str] = set()  # ücretsiz plan: 3 farklı numara

    def can_send(self) -> bool:
        if self._sent_today >= self._daily_limit:
            return False
        return True

    def can_send_to(self, phone: str) -> bool:
        """Ücretsiz planda 3 farklı numaraya kadar."""
        chat_id = _format_phone(phone)
        if not chat_id:
            return False
        if chat_id in self._sent_numbers:
            return True  # daha önce gönderdiğimiz numaraya tekrar gönderebiliriz
        return len(self._sent_numbers) < self.FREE_TIER_CONTACT_LIMIT

    @property
    def stats(self) -> str:
        return (f"WA bugün: {self._sent_today}/{self._daily_limit} | "
                f"benzersiz numara: {len(self._sent_numbers)}/{self.FREE_TIER_CONTACT_LIMIT} (ücretsiz plan)")

    async def send(self, phone: str, message: str) -> bool:
        chat_id = _format_phone(phone)
        if not chat_id:
            logger.warning(f"WA: Geçersiz telefon numarası: {phone}")
            return False
        if not self.can_send():
            logger.warning("WA: Günlük limit doldu")
            return False
        if not self.can_send_to(phone):
            logger.warning(f"WA: Ücretsiz plan 3 numara limiti doldu — {phone}")
            return False

        url = f"{_BASE}/waInstance{self._id}/sendMessage/{self._token}"
        payload = {"chatId": chat_id, "message": message}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload,
                                        timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("idMessage"):
                            self._sent_today += 1
                            self._sent_numbers.add(chat_id)
                            logger.info(f"WA gönderildi: {chat_id}")
                            return True
                    body = await resp.text()
                    logger.warning(f"WA hata {resp.status}: {body[:200]}")
                    return False
        except Exception as e:
            logger.error(f"WA istek hatası: {e}")
            return False

    async def check_state(self) -> str:
        """Instance durumu: authorized / notAuthorized / blocked"""
        url = f"{_BASE}/waInstance{self._id}/getStateInstance/{self._token}"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status == 200:
                        d = await r.json()
                        return d.get("stateInstance", "unknown")
        except Exception:
            pass
        return "error"


def init_whatsapp() -> "WhatsAppClient | None":
    global _instance
    from config import settings
    inst_id = getattr(settings, "greenapi_instance_id", "")
    token   = getattr(settings, "greenapi_api_token", "")
    if not inst_id or not token:
        logger.info("WhatsApp: GREENAPI_INSTANCE_ID veya GREENAPI_API_TOKEN eksik, devre dışı")
        return None
    _instance = WhatsAppClient(inst_id, token)
    logger.info(f"WhatsApp: Green-API instance {inst_id} hazır")
    return _instance


def get_whatsapp() -> "WhatsAppClient | None":
    return _instance
