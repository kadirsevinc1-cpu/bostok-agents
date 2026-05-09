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
    def __init__(self, user: str, app_password: str, daily_limit: int = 25,
                 smtp_host: str = "smtp.gmail.com", smtp_port: int = 465, use_tls: bool = True,
                 from_email: str = "", reply_to: str = ""):
        self._user = user
        self._password = app_password
        self._from_email = from_email or user   # SMTP login'den farklı From adresi (Brevo için)
        self._reply_to = reply_to or self._from_email
        self._limit = daily_limit
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._use_tls = use_tls
        self._count_file = Path(f"memory/gmail_count_{user.split('@')[0]}.json")
        self._today_count, self._last_date = self._load_count()
        self._sent: set[str] = self._load_sent()

    def _load_count(self) -> tuple[int, date]:
        if self._count_file.exists():
            try:
                data = json.loads(self._count_file.read_text(encoding="utf-8"))
                saved_date = date.fromisoformat(data["date"])
                if saved_date == date.today():
                    logger.info(f"Gmail sayac yuklendi: {data['count']} mail bugun gonderildi ({self._user if hasattr(self, '_user') else ''})")
                    return data["count"], saved_date
            except Exception:
                pass
        return 0, date.today()

    def _save_count(self):
        self._count_file.parent.mkdir(exist_ok=True)
        tmp = self._count_file.with_suffix(".tmp")
        tmp.write_text(json.dumps({"date": self._last_date.isoformat(), "count": self._today_count}), encoding="utf-8")
        os.replace(tmp, self._count_file)

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
            self._save_count()

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
            _ev_loop = asyncio.get_running_loop()
            _ev_valid = await _ev_loop.run_in_executor(None, _email_valid, to)
            if not _ev_valid:
                return False
        except Exception:
            pass
        if not self.can_send():
            logger.warning(f"Gunluk mail limiti doldu: {self._limit}")
            return False
        try:
            msg_id = f"<{uuid.uuid4().hex}@bostok.dev>"
            msg = MIMEMultipart("alternative")
            msg["From"] = f"Kadir Sevinç <{self._from_email}>"
            msg["To"] = to
            msg["Subject"] = subject
            msg["Message-ID"] = msg_id
            msg["Reply-To"] = self._reply_to
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
                from integrations.tracking_server import get_tracking_url, get_unsub_url
                pixel_url = get_tracking_url(msg_id)
                pixel_tag = f'<img src="{pixel_url}" width="1" height="1" style="display:none" alt=""/>' if pixel_url else ""
                unsub_url = get_unsub_url(msg_id)
            except Exception:
                pixel_tag = ""
                unsub_url = ""

            unsub_footer = (
                f'<div style="margin-top:32px;padding-top:16px;border-top:1px solid #e2e8f0;'
                f'font-size:11px;color:#94a3b8;text-align:center">'
                f'<a href="{unsub_url}" style="color:#94a3b8;text-decoration:underline">Unsubscribe</a>'
                f' &nbsp;·&nbsp; Bostok.dev</div>'
            ) if unsub_url else ""

            html_body = (
                f'<html><body style="font-family:Arial,sans-serif;font-size:14px;'
                f'color:#222;max-width:600px;margin:0 auto;padding:20px">'
                f'{html_body}{unsub_footer}{pixel_tag}</body></html>'
            )
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._smtp_send, to, msg.as_string())
            self._today_count += 1
            self._save_count()
            self._record_sent(to)
            self._save_message_id(msg_id, to, subject, lead_info or {})
            try:
                from core.ab_tracker import record_sent as ab_sent
                info = lead_info or {}
                ab_sent(msg_id, subject, info.get("sector", ""), info.get("lang", ""))
            except Exception:
                pass
            logger.info(f"Mail gonderildi: {to} ({self._today_count}/{self._limit})")
            # Decision log (TradingAgents'tan ilham — Apache 2.0)
            try:
                import json as _json
                from pathlib import Path as _P
                _dlog = _P("memory/decision_log.jsonl")
                _dlog.parent.mkdir(exist_ok=True)
                info = lead_info or {}
                entry = {
                    "ts": __import__("datetime").datetime.now().isoformat(),
                    "to": to,
                    "subject": subject[:120],
                    "sector": info.get("sector", ""),
                    "location": info.get("location", ""),
                    "lang": info.get("lang", ""),
                    "has_website": info.get("has_website", False),
                    "msg_id": msg_id,
                }
                with _dlog.open("a", encoding="utf-8") as _f:
                    _f.write(_json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                pass
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
            self._save_count()
            logger.info(f"Yanit gonderildi: {to} ({self._today_count}/{self._limit})")
            return True
        except Exception as e:
            logger.error(f"Yanit hata [{to}]: {e}")
            return False

    def _smtp_send(self, to: str, raw: str):
        if self._use_tls:
            with smtplib.SMTP_SSL(self._smtp_host, self._smtp_port, timeout=30) as srv:
                srv.login(self._user, self._password)
                srv.sendmail(self._user, to, raw)
        else:
            with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=30) as srv:
                srv.ehlo()
                srv.starttls()
                srv.login(self._user, self._password)
                srv.sendmail(self._user, to, raw)


class GmailPool:
    """Round-robin ile birden fazla Gmail hesabı yönetir."""

    def __init__(self, senders: list[GmailSender]):
        self._senders = senders
        self._idx = 0

    def _next(self) -> GmailSender | None:
        # smtp.gmail.com Google Cloud'da bloklu (525) — Brevo/Outlook varsa Gmail'i atla
        non_gmail = [s for s in self._senders if s._smtp_host != "smtp.gmail.com"]
        pool = non_gmail if non_gmail else self._senders
        return next((s for s in pool if s.can_send()), None)

    def can_send(self) -> bool:
        return any(s.can_send() for s in self._senders)

    def is_sent(self, email: str) -> bool:
        return any(s.is_sent(email) for s in self._senders) if self._senders else False

    @property
    def stats(self) -> str:
        def _label(s):
            user = getattr(s, "_user", None) or getattr(s, "_from_email", "?")
            return f"{user.split('@')[0]}: {s._today_count}/{s._limit}"
        return " | ".join(_label(s) for s in self._senders)

    def _candidates(self):
        """Google Cloud'da smtp.gmail.com bloklu (525) — Gmail'i atla; yoksa tüm liste."""
        blocked = {"smtp.gmail.com"}
        ok = [s for s in self._senders if getattr(s, "_smtp_host", "") not in blocked]
        return ok if ok else self._senders

    async def send(self, to: str, subject: str, body: str, lead_info: dict = None) -> bool:
        for s in self._candidates():
            if not s.can_send():
                continue
            ok = await s.send(to, subject, body, lead_info)
            if ok:
                return True
            # SMTP bağlantı hatası — sonraki göndericiyi dene
        logger.warning("Tüm hesaplar limitinde veya bağlantı hatası")
        return False

    async def send_reply(self, to: str, subject: str, body: str, in_reply_to: str = "") -> bool:
        # Resend önce — IP kısıtlaması yok, günlük limit aşılsa bile yanıt öncelikli
        resend = next((s for s in self._senders if isinstance(s, ResendSender)), None)
        if resend:
            ok = await resend.send_reply(to, subject, body, in_reply_to)
            if ok:
                return True
        # Fallback: Brevo ve diğerleri
        for s in self._candidates():
            if isinstance(s, ResendSender):
                continue  # zaten denendi
            if not s.can_send():
                continue
            ok = await s.send_reply(to, subject, body, in_reply_to)
            if ok:
                return True
        logger.warning("send_reply: tüm hesaplar başarısız")
        return False


class ResendSender:
    """Resend.com HTTP API ile mail gönderici — IP kısıtlaması yok."""

    def __init__(self, api_key: str, from_email: str, reply_to: str = "", daily_limit: int = 100):
        self._api_key = api_key
        self._from_email = from_email
        self._reply_to = reply_to or from_email
        self._limit = daily_limit
        self._smtp_host = "api.resend.com"  # _candidates() filtresi için
        self._count_file = Path(f"memory/resend_count.json")
        self._today_count, self._last_date = self._load_count()
        self._sent: set[str] = self._load_sent()

    def _load_count(self) -> tuple[int, date]:
        if self._count_file.exists():
            try:
                data = json.loads(self._count_file.read_text(encoding="utf-8"))
                if date.fromisoformat(data["date"]) == date.today():
                    return data["count"], date.today()
            except Exception:
                pass
        return 0, date.today()

    def _save_count(self):
        self._count_file.parent.mkdir(exist_ok=True)
        tmp = self._count_file.with_suffix(".tmp")
        tmp.write_text(json.dumps({"date": self._last_date.isoformat(), "count": self._today_count}), encoding="utf-8")
        os.replace(tmp, self._count_file)

    def _load_sent(self) -> set[str]:
        if SENT_LOG.exists():
            return set(SENT_LOG.read_text(encoding="utf-8").splitlines())
        return set()

    def _record_sent(self, email: str):
        SENT_LOG.parent.mkdir(exist_ok=True)
        with SENT_LOG.open("a", encoding="utf-8") as f:
            f.write(email + "\n")
        self._sent.add(email)

    def _reset_if_new_day(self):
        today = date.today()
        if today != self._last_date:
            self._today_count = 0
            self._last_date = today
            self._save_count()

    def can_send(self) -> bool:
        self._reset_if_new_day()
        return self._today_count < self._limit

    def is_sent(self, email: str) -> bool:
        return email.strip().lower() in self._sent

    def _post(self, payload: dict) -> bool:
        import requests as _req
        r = _req.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            json=payload, timeout=20,
        )
        if r.status_code != 200:
            raise Exception(f"HTTP {r.status_code}: {r.text[:200]}")
        return True

    async def send(self, to: str, subject: str, body: str, lead_info: dict = None) -> bool:
        self._reset_if_new_day()
        to = to.strip().lower()
        if to in self._sent or to in load_bounced() or not self.can_send():
            return False
        try:
            from integrations.email_validator import is_valid as _ev
            loop = asyncio.get_running_loop()
            if not await loop.run_in_executor(None, _ev, to):
                return False
        except Exception:
            pass
        try:
            html = body.replace("\n", "<br>\n")
            html = re.sub(r'(https?://[^\s<>"]+)', r'<a href="\1">\1</a>', html)
            payload = {
                "from": f"Kadir Sevinç <{self._from_email}>",
                "to": [to], "subject": subject,
                "text": body, "html": f"<html><body style='font-family:Arial,sans-serif;font-size:14px'>{html}</body></html>",
                "reply_to": self._reply_to,
            }
            loop = asyncio.get_running_loop()
            ok = await loop.run_in_executor(None, self._post, payload)
            if ok:
                self._today_count += 1
                self._save_count()
                self._record_sent(to)
                logger.info(f"Resend gonderildi: {to} ({self._today_count}/{self._limit})")
                return True
        except Exception as e:
            logger.error(f"Resend hata [{to}]: {e}")
        return False

    async def send_reply(self, to: str, subject: str, body: str, in_reply_to: str = "") -> bool:
        self._reset_if_new_day()
        if not self.can_send():
            return False
        try:
            payload = {
                "from": f"Kadir Sevinç <{self._from_email}>",
                "to": [to.strip()], "subject": subject, "text": body,
                "reply_to": self._reply_to,
            }
            loop = asyncio.get_running_loop()
            ok = await loop.run_in_executor(None, self._post, payload)
            if ok:
                self._today_count += 1
                self._save_count()
                logger.info(f"Resend yanit: {to} ({self._today_count}/{self._limit})")
                return True
        except Exception as e:
            logger.error(f"Resend yanit hata [{to}]: {e}")
        return False


class MailjetSender:
    """Mailjet HTTP API ile mail gönderici — IP kısıtlaması yok, 200/gün ücretsiz."""

    def __init__(self, api_key: str, secret_key: str, from_email: str, reply_to: str = "", daily_limit: int = 200):
        self._api_key = api_key
        self._secret_key = secret_key
        self._from_email = from_email
        self._reply_to = reply_to or from_email
        self._limit = daily_limit
        self._smtp_host = "api.mailjet.com"
        self._count_file = Path("memory/mailjet_count.json")
        self._today_count, self._last_date = self._load_count()
        self._sent: set[str] = self._load_sent()

    def _load_count(self) -> tuple[int, date]:
        if self._count_file.exists():
            try:
                data = json.loads(self._count_file.read_text(encoding="utf-8"))
                if date.fromisoformat(data["date"]) == date.today():
                    return data["count"], date.today()
            except Exception:
                pass
        return 0, date.today()

    def _save_count(self):
        self._count_file.parent.mkdir(exist_ok=True)
        tmp = self._count_file.with_suffix(".tmp")
        tmp.write_text(json.dumps({"date": self._last_date.isoformat(), "count": self._today_count}), encoding="utf-8")
        os.replace(tmp, self._count_file)

    def _load_sent(self) -> set[str]:
        if SENT_LOG.exists():
            return set(SENT_LOG.read_text(encoding="utf-8").splitlines())
        return set()

    def _record_sent(self, email: str):
        SENT_LOG.parent.mkdir(exist_ok=True)
        with SENT_LOG.open("a", encoding="utf-8") as f:
            f.write(email + "\n")
        self._sent.add(email)

    def _reset_if_new_day(self):
        today = date.today()
        if today != self._last_date:
            self._today_count = 0
            self._last_date = today
            self._save_count()

    def can_send(self) -> bool:
        self._reset_if_new_day()
        return self._today_count < self._limit

    def is_sent(self, email: str) -> bool:
        return email.strip().lower() in self._sent

    def _post(self, payload: dict) -> bool:
        import requests as _req
        r = _req.post(
            "https://api.mailjet.com/v3.1/send",
            auth=(self._api_key, self._secret_key),
            json=payload, timeout=20,
        )
        if r.status_code not in (200, 201):
            raise Exception(f"HTTP {r.status_code}: {r.text[:200]}")
        return True

    def _build_payload(self, to: str, subject: str, body: str, in_reply_to: str = "") -> dict:
        html = body.replace("\n", "<br>\n")
        html = re.sub(r'(https?://[^\s<>"]+)', r'<a href="\1">\1</a>', html)
        msg: dict = {
            "From": {"Email": self._from_email, "Name": "Kadir Sevinç"},
            "To": [{"Email": to}],
            "Subject": subject,
            "TextPart": body,
            "HTMLPart": f"<html><body style='font-family:Arial,sans-serif;font-size:14px'>{html}</body></html>",
            "ReplyTo": {"Email": self._reply_to},
        }
        if in_reply_to:
            msg["Headers"] = {"In-Reply-To": in_reply_to}
        return {"Messages": [msg]}

    async def send(self, to: str, subject: str, body: str, lead_info: dict = None) -> bool:  # noqa: ARG002
        self._reset_if_new_day()
        to = to.strip().lower()
        if to in self._sent or to in load_bounced() or not self.can_send():
            return False
        try:
            from integrations.email_validator import is_valid as _ev
            loop = asyncio.get_running_loop()
            if not await loop.run_in_executor(None, _ev, to):
                return False
        except Exception:
            pass
        try:
            payload = self._build_payload(to, subject, body)
            loop = asyncio.get_running_loop()
            ok = await loop.run_in_executor(None, self._post, payload)
            if ok:
                self._today_count += 1
                self._save_count()
                self._record_sent(to)
                logger.info(f"Mailjet gonderildi: {to} ({self._today_count}/{self._limit})")
                return True
        except Exception as e:
            logger.error(f"Mailjet hata [{to}]: {e}")
        return False

    async def send_reply(self, to: str, subject: str, body: str, in_reply_to: str = "") -> bool:
        self._reset_if_new_day()
        if not self.can_send():
            return False
        try:
            payload = self._build_payload(to.strip(), subject, body, in_reply_to)
            loop = asyncio.get_running_loop()
            ok = await loop.run_in_executor(None, self._post, payload)
            if ok:
                self._today_count += 1
                self._save_count()
                logger.info(f"Mailjet yanit: {to} ({self._today_count}/{self._limit})")
                return True
        except Exception as e:
            logger.error(f"Mailjet yanit hata [{to}]: {e}")
        return False


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

        # Brevo SMTP (kadir@bostok.dev'den gönderir — spam sorunu yok)
        brevo_user = getattr(settings, "brevo_smtp_user", "")
        brevo_key  = getattr(settings, "brevo_smtp_key", "")
        brevo_from = getattr(settings, "brevo_from_email", "")
        brevo_limit = int(getattr(settings, "brevo_daily_limit", 300))
        if brevo_user and brevo_key:
            s = GmailSender(
                user=brevo_user, app_password=brevo_key,
                daily_limit=brevo_limit,
                smtp_host="smtp.brevo.com", smtp_port=587, use_tls=False,
                from_email=brevo_from or brevo_user,
                reply_to=getattr(settings, "gmail_user", "") or brevo_from,
            )
            senders.insert(0, s)  # Brevo önce gelsin
            logger.info(f"Brevo hazir: {brevo_from or brevo_user} (limit: {brevo_limit}/gun)")

        # Outlook hesapları
        outlook_accounts = [
            (getattr(settings, "outlook_user", ""),
             getattr(settings, "outlook_app_password", ""),
             int(getattr(settings, "outlook_daily_limit", 300)),
             int(getattr(settings, "outlook_account_age_days", 0))),
            (getattr(settings, "outlook_user_2", ""),
             getattr(settings, "outlook_app_password_2", ""),
             int(getattr(settings, "outlook_daily_limit_2", 300)),
             int(getattr(settings, "outlook_account_age_days_2", 0))),
        ]
        for user, pwd, limit, age_days in outlook_accounts:
            if user and pwd:
                effective = _warmup_limit(age_days, limit)
                s = GmailSender(user, pwd, daily_limit=effective,
                                smtp_host="smtp-mail.outlook.com", smtp_port=587, use_tls=False)
                senders.append(s)
                warmup_note = f" [ısınma: {effective}/{limit}]" if effective < limit else ""
                logger.info(f"Outlook hazir: {user} (limit: {effective}{warmup_note})")

        # Resend HTTP API (IP kısıtlaması yok)
        resend_key   = getattr(settings, "resend_api_key", "")
        resend_from  = getattr(settings, "resend_from_email", "kadir@bostok.dev")
        resend_limit = int(getattr(settings, "resend_daily_limit", 100))
        if resend_key:
            rs = ResendSender(resend_key, resend_from,
                              reply_to=getattr(settings, "gmail_user", "") or resend_from,
                              daily_limit=resend_limit)
            senders.insert(0, rs)  # Resend önce — en güvenilir
            logger.info(f"Resend hazir: {resend_from} (limit: {resend_limit}/gun)")

        # Mailjet HTTP API (IP kısıtlaması yok, 200/gün ücretsiz)
        mj_key    = getattr(settings, "mailjet_api_key", "")
        mj_secret = getattr(settings, "mailjet_secret_key", "")
        mj_from   = getattr(settings, "mailjet_from_email", "kadir@bostok.dev")
        mj_limit  = int(getattr(settings, "mailjet_daily_limit", 200))
        if mj_key and mj_secret:
            mj = MailjetSender(mj_key, mj_secret, mj_from,
                               reply_to=getattr(settings, "gmail_user", "") or mj_from,
                               daily_limit=mj_limit)
            senders.append(mj)
            logger.info(f"Mailjet hazir: {mj_from} (limit: {mj_limit}/gun)")

        if not senders:
            return None
        if len(senders) == 1:
            _sender = senders[0]
        else:
            _sender = GmailPool(senders)
            logger.info(f"Mail havuzu: {len(senders)} hesap")
        return _sender
    except Exception as e:
        logger.warning(f"Gmail init hata: {e}")
    return None


def get_gmail() -> GmailSender | GmailPool | None:
    return _sender
