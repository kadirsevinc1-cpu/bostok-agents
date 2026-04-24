"""Gmail SMTP ile mail gönderme — günlük limit, tekrar önleme, yanıt takibi."""
import asyncio
import json
import smtplib
import uuid
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from loguru import logger

SENT_LOG = Path("memory/sent_emails.txt")
SENT_IDS_FILE = Path("memory/sent_message_ids.json")


class GmailSender:
    def __init__(self, user: str, app_password: str, daily_limit: int = 25):
        self._user = user
        self._password = app_password
        self._limit = daily_limit
        self._today_count = 0
        self._last_date = date.today()
        self._sent: set[str] = self._load_sent()

    def _load_sent(self) -> set[str]:
        if SENT_LOG.exists():
            return set(SENT_LOG.read_text(encoding="utf-8").splitlines())
        return set()

    def _record_sent(self, email: str):
        SENT_LOG.parent.mkdir(exist_ok=True)
        with SENT_LOG.open("a", encoding="utf-8") as f:
            f.write(email + "\n")
        self._sent.add(email)

    def _save_message_id(self, msg_id: str, to: str, subject: str, lead_info: dict):
        SENT_IDS_FILE.parent.mkdir(exist_ok=True)
        data = {}
        if SENT_IDS_FILE.exists():
            try:
                data = json.loads(SENT_IDS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        data[msg_id] = {
            "to": to,
            "subject": subject,
            "sent_at": datetime.now().isoformat(),
            **lead_info,
        }
        SENT_IDS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _reset_if_new_day(self):
        today = date.today()
        if today != self._last_date:
            self._today_count = 0
            self._last_date = today

    @property
    def stats(self) -> str:
        self._reset_if_new_day()
        return f"Bugun: {self._today_count}/{self._limit} mail gonderildi"

    def can_send(self) -> bool:
        self._reset_if_new_day()
        return self._today_count < self._limit

    async def send(self, to: str, subject: str, body: str, lead_info: dict = None) -> bool:
        if not self._user or not self._password:
            logger.warning("Gmail yapilandirilmamis")
            return False
        self._reset_if_new_day()
        to = to.strip().lower()
        if to in self._sent:
            logger.debug(f"Zaten gonderildi: {to}")
            return False
        if not self.can_send():
            logger.warning(f"Gunluk mail limiti doldu: {self._limit}")
            return False
        try:
            msg_id = f"<{uuid.uuid4().hex}@bostok.dev>"
            msg = MIMEMultipart()
            msg["From"] = self._user
            msg["To"] = to
            msg["Subject"] = subject
            msg["Message-ID"] = msg_id
            msg.attach(MIMEText(body, "plain", "utf-8"))
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._smtp_send, to, msg.as_string())
            self._today_count += 1
            self._record_sent(to)
            self._save_message_id(msg_id, to, subject, lead_info or {})
            logger.info(f"Mail gonderildi: {to} ({self._today_count}/{self._limit})")
            return True
        except Exception as e:
            logger.error(f"Mail hata [{to}]: {e}")
            return False

    async def send_reply(self, to: str, subject: str, body: str, in_reply_to: str = "") -> bool:
        """Lead'e kişisel yanıt gönder — deduplication kontrolü yok."""
        if not self._user or not self._password:
            logger.warning("Gmail yapilandirilmamis")
            return False
        self._reset_if_new_day()
        if not self.can_send():
            logger.warning(f"Gunluk mail limiti doldu: {self._limit}")
            return False
        try:
            msg = MIMEMultipart()
            msg["From"] = self._user
            msg["To"] = to.strip()
            msg["Subject"] = subject
            msg["Message-ID"] = f"<{uuid.uuid4().hex}@bostok.dev>"
            if in_reply_to:
                msg["In-Reply-To"] = in_reply_to
                msg["References"] = in_reply_to
            msg.attach(MIMEText(body, "plain", "utf-8"))
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._smtp_send, to.strip(), msg.as_string())
            self._today_count += 1
            logger.info(f"Yanit gonderildi: {to} ({self._today_count}/{self._limit})")
            return True
        except Exception as e:
            logger.error(f"Yanit hata [{to}]: {e}")
            return False

    def _smtp_send(self, to: str, raw: str):
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as srv:
            srv.login(self._user, self._password)
            srv.sendmail(self._user, to, raw)


_sender: GmailSender | None = None


def init_gmail() -> GmailSender | None:
    global _sender
    try:
        from config import settings
        user = getattr(settings, "gmail_user", "")
        pwd = getattr(settings, "gmail_app_password", "")
        if user and pwd:
            _sender = GmailSender(user, pwd)
            logger.info(f"Gmail hazir: {user}")
            return _sender
    except Exception as e:
        logger.warning(f"Gmail init hata: {e}")
    return None


def get_gmail() -> GmailSender | None:
    return _sender
