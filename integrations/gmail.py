"""Gmail SMTP ile mail gönderme — günlük limit, tekrar önleme, yanıt takibi."""
import asyncio
import json
import os
import re
import smtplib
import uuid
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from loguru import logger

SENT_LOG      = Path("memory/sent_emails.txt")
SENT_IDS_FILE = Path("memory/sent_message_ids.json")
BOUNCE_LOG    = Path("memory/bounced_emails.txt")


def _warmup_limit(account_age_days: int, configured_limit: int) -> int:
    """Hesap yaşına göre günlük limit uygula (spam önleme)."""
    if account_age_days < 7:
        return min(20, configured_limit)
    if account_age_days < 14:
        return min(50, configured_limit)
    if account_age_days < 30:
        return min(150, configured_limit)
    return configured_limit

_BOUNCE_SENDERS = {
    "mailer-daemon", "postmaster", "noreply@", "no-reply@",
    "mail-daemon", "delivery-failure", "bounce",
}


def is_bounce(from_email: str) -> bool:
    f = from_email.lower()
    return any(s in f for s in _BOUNCE_SENDERS)


def record_bounce(email: str):
    """Bounce olan adresi kalıcı olarak kaydet."""
    BOUNCE_LOG.parent.mkdir(exist_ok=True)
    existing = set(BOUNCE_LOG.read_text(encoding="utf-8").splitlines()) if BOUNCE_LOG.exists() else set()
    if email not in existing:
        with BOUNCE_LOG.open("a", encoding="utf-8") as f:
            f.write(email + "\n")
        logger.info(f"Bounce kaydedildi: {email}")


def load_bounced() -> set:
    if BOUNCE_LOG.exists():
        return set(BOUNCE_LOG.read_text(encoding="utf-8").splitlines())
    return set()


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
            except Exception as e:
                logger.error(f"sent_message_ids.json okunamadi: {e}")
        data[msg_id] = {
            "to": to,
            "subject": subject,
            "sent_at": datetime.now().isoformat(),
            **lead_info,
        }
        tmp = SENT_IDS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, SENT_IDS_FILE)

    def _reset_if_new_day(self):
        today = date.today()
        if today != self._last_date:
            self._today_count = 0
            self._last_date = today

    @property
    def stats(self) -> str:
        self._reset_if_new_day()
        return f"Bugun: {self._today_count}/{self._limit} mail gonderildi"

    def is_sent(self, email: str) -> bool:
        return email.strip().lower() in self._sent

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
        if to in load_bounced():
            logger.debug(f"Bounce listesinde, atlanıyor: {to}")
            return False
        try:
            from integrations.email_validator import is_valid as _email_valid
            if not _email_valid(to):
                return False
        except Exception:
            pass
        if not self.can_send():
            logger.warning(f"Gunluk mail limiti doldu: {self._limit}")
            return False
        try:
            msg_id = f"<{uuid.uuid4().hex}@bostok.dev>"
            msg = MIMEMultipart("alternative")
            msg["From"] = f"Kadir Sevinç <{self._user}>"
            msg["To"] = to
            msg["Subject"] = subject
            msg["Message-ID"] = msg_id
            msg["Reply-To"] = self._user
            msg["List-Unsubscribe"] = f"<mailto:{self._user}?subject=unsubscribe>"
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

            # Plain text (spam filtreler için gerekli)
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # HTML versiyonu — satır sonlarını <br> yap, link'leri tıklanabilir hale getir
            html_body = body.replace("\n", "<br>\n")
            html_body = re.sub(
                r'(https?://[^\s<>"]+)',
                r'<a href="\1">\1</a>',
                html_body
            )
            # Tracking pixel
            try:
                from integrations.tracking_server import get_tracking_url
                pixel_url = get_tracking_url(msg_id)
                pixel_tag = f'<img src="{pixel_url}" width="1" height="1" style="display:none" alt=""/>' if pixel_url else ""
            except Exception:
                pixel_tag = ""
            html_body = (
                f'<html><body style="font-family:Arial,sans-serif;font-size:14px;'
                f'color:#222;max-width:600px;margin:0 auto;padding:20px">'
                f'{html_body}{pixel_tag}</body></html>'
            )
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._smtp_send, to, msg.as_string())
            self._today_count += 1
            self._record_sent(to)
            self._save_message_id(msg_id, to, subject, lead_info or {})
            try:
                from core.ab_tracker import record_sent as ab_sent
                info = lead_info or {}
                ab_sent(msg_id, subject, info.get("sector", ""), info.get("lang", ""))
            except Exception:
                pass
            logger.info(f"Mail gonderildi: {to} ({self._today_count}/{self._limit})")
            try:
                from core.lead_state import get_tracker, LeadStage
                info = lead_info or {}
                tracker = get_tracker()
                tracker.upsert(to, name=info.get("name", ""), sector=info.get("sector", ""), location=info.get("location", ""), phone=info.get("phone", ""))
                tracker.update(to, LeadStage.CONTACTED, f"Konu: {subject[:80]}")
            except Exception:
                pass
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
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._smtp_send, to.strip(), msg.as_string())
            self._today_count += 1
            logger.info(f"Yanit gonderildi: {to} ({self._today_count}/{self._limit})")
            return True
        except Exception as e:
            logger.error(f"Yanit hata [{to}]: {e}")
            return False

    def _smtp_send(self, to: str, raw: str):
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as srv:
            srv.login(self._user, self._password)
            srv.sendmail(self._user, to, raw)


class GmailPool:
    """Round-robin ile birden fazla Gmail hesabı yönetir."""

    def __init__(self, senders: list[GmailSender]):
        self._senders = senders
        self._idx = 0

    def _next(self) -> GmailSender | None:
        for _ in range(len(self._senders)):
            s = self._senders[self._idx % len(self._senders)]
            self._idx += 1
            if s.can_send():
                return s
        return None

    def can_send(self) -> bool:
        return any(s.can_send() for s in self._senders)

    def is_sent(self, email: str) -> bool:
        return self._senders[0].is_sent(email) if self._senders else False

    @property
    def stats(self) -> str:
        return " | ".join(
            f"{s._user.split('@')[0]}: {s._today_count}/{s._limit}"
            for s in self._senders
        )

    async def send(self, to: str, subject: str, body: str, lead_info: dict = None) -> bool:
        s = self._next()
        if not s:
            logger.warning("Tüm Gmail hesapları limitinde")
            return False
        return await s.send(to, subject, body, lead_info)

    async def send_reply(self, to: str, subject: str, body: str, in_reply_to: str = "") -> bool:
        s = self._next() or (self._senders[0] if self._senders else None)
        if not s:
            return False
        return await s.send_reply(to, subject, body, in_reply_to)


_sender: GmailSender | GmailPool | None = None


def init_gmail() -> GmailSender | GmailPool | None:
    global _sender
    try:
        from config import settings
        senders = []
        accounts = [
            (getattr(settings, "gmail_user", ""),
             getattr(settings, "gmail_app_password", ""),
             int(getattr(settings, "gmail_daily_limit", 500)),
             int(getattr(settings, "gmail_account_age_days", 365))),
            (getattr(settings, "gmail_user_2", ""),
             getattr(settings, "gmail_app_password_2", ""),
             int(getattr(settings, "gmail_daily_limit_2", 500)),
             int(getattr(settings, "gmail_account_age_days_2", 365))),
            (getattr(settings, "gmail_user_3", ""),
             getattr(settings, "gmail_app_password_3", ""),
             int(getattr(settings, "gmail_daily_limit_3", 500)),
             int(getattr(settings, "gmail_account_age_days_3", 365))),
        ]
        for user, pwd, limit, age_days in accounts:
            if user and pwd:
                effective = _warmup_limit(age_days, limit)
                s = GmailSender(user, pwd, daily_limit=effective)
                senders.append(s)
                warmup_note = f" [ısınma: {effective}/{limit}]" if effective < limit else ""
                logger.info(f"Gmail hazir: {user} (limit: {effective}{warmup_note})")

        if not senders:
            return None
        if len(senders) == 1:
            _sender = senders[0]
        else:
            _sender = GmailPool(senders)
            logger.info(f"Gmail havuzu: {len(senders)} hesap")
        return _sender
    except Exception as e:
        logger.warning(f"Gmail init hata: {e}")
    return None


def get_gmail() -> GmailSender | GmailPool | None:
    return _sender
