"""
Telegram entegrasyonu — bildirim gönder, onay bekle, komut al.
"""
import asyncio
import aiohttp
from loguru import logger

BASE_URL = "https://api.telegram.org/bot{token}"


class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self._base = f"https://api.telegram.org/bot{token}"
        self._offset = 0
        self._pending_approvals: dict[str, asyncio.Event] = {}
        self._pending_results: dict[str, str] = {}

    async def send(self, text: str, reply_markup: dict = None):
        """Mesaj gönder."""
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            import json
            payload["reply_markup"] = json.dumps(reply_markup)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self._base}/sendMessage", json=payload) as resp:
                    data = await resp.json()
                    if not data.get("ok"):
                        logger.warning(f"Telegram send hatasi: {data}")
        except Exception as e:
            logger.error(f"Telegram send error: {e}")

    async def request_approval(self, approval_id: str, message: str) -> bool:
        """Onay iste, kullanıcı /onayla veya /reddet yazana kadar bekle."""
        event = asyncio.Event()
        self._pending_approvals[approval_id] = event
        self._pending_results[approval_id] = "pending"

        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Onayla", "callback_data": f"approve_{approval_id}"},
                {"text": "❌ Reddet", "callback_data": f"reject_{approval_id}"},
            ]]
        }
        await self.send(f"⏳ <b>Onay Gerekiyor</b>\n\n{message}", reply_markup=keyboard)

        try:
            await asyncio.wait_for(event.wait(), timeout=86400)  # 24 saat bekle
            return self._pending_results.get(approval_id) == "approved"
        except asyncio.TimeoutError:
            await self.send("Onay 24 saat icinde verilmedi, islem iptal edildi.")
            return False
        finally:
            self._pending_approvals.pop(approval_id, None)
            self._pending_results.pop(approval_id, None)

    async def poll_updates(self, on_message, on_callback=None):
        """Sürekli güncelleme al — komutları işle."""
        logger.info("Telegram polling başladı")
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self._base}/getUpdates",
                        params={"offset": self._offset, "timeout": 30},
                        timeout=aiohttp.ClientTimeout(total=35),
                    ) as resp:
                        data = await resp.json()

                if not data.get("ok"):
                    await asyncio.sleep(5)
                    continue

                for update in data.get("result", []):
                    self._offset = update["update_id"] + 1

                    # Callback (inline buton)
                    if "callback_query" in update:
                        cb = update["callback_query"]
                        callback_data = cb.get("data", "")
                        await self._handle_callback(callback_data)
                        if on_callback:
                            await on_callback(callback_data)
                        # Butonu temizle
                        try:
                            async with aiohttp.ClientSession() as s:
                                await s.post(f"{self._base}/answerCallbackQuery",
                                            json={"callback_query_id": cb["id"]})
                        except Exception:
                            pass

                    # Normal mesaj
                    elif "message" in update:
                        msg = update["message"]
                        text = msg.get("text", "")
                        chat_id = str(msg.get("chat", {}).get("id", ""))
                        if chat_id == self.chat_id and text and on_message:
                            await on_message(text)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Telegram poll hatasi: {e}")
                await asyncio.sleep(5)

    async def _handle_callback(self, data: str):
        """Inline buton callback'lerini işle."""
        if data.startswith("approve_"):
            approval_id = data[8:]
            if approval_id in self._pending_approvals:
                self._pending_results[approval_id] = "approved"
                self._pending_approvals[approval_id].set()
                await self.send("✅ Onaylandı!")
        elif data.startswith("reject_"):
            approval_id = data[7:]
            if approval_id in self._pending_approvals:
                self._pending_results[approval_id] = "rejected"
                self._pending_approvals[approval_id].set()
                await self.send("❌ Reddedildi.")


_bot: TelegramBot | None = None


def get_bot() -> TelegramBot | None:
    return _bot


def init_bot() -> TelegramBot | None:
    global _bot
    try:
        from config import settings
        if settings.telegram_bot_token and settings.telegram_chat_id:
            _bot = TelegramBot(settings.telegram_bot_token, settings.telegram_chat_id)
            logger.info("Telegram bot hazir")
            return _bot
    except Exception as e:
        logger.warning(f"Telegram init hatasi: {e}")
    return None
