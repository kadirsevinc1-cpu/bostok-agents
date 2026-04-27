"""Gmail IMAP okuyucu — sadece bizim outreach maillerimize gelen yanıtları filtreler."""
import email as email_lib
import email.utils
import hashlib
import imaplib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path
from loguru import logger

SENT_IDS_FILE = Path("memory/sent_message_ids.json")
SEEN_UIDS_FILE = Path("memory/seen_reply_uids.txt")
INBOX_EMAILS_FILE = Path("memory/inbox_emails.json")


@dataclass
class InboxReply:
    reply_id: str
    uid: str
    from_email: str
    from_name: str
    subject: str
    body: str
    sent_info: dict
    matched_message_id: str
    received_at: str


class GmailReader:
    def __init__(self, user: str, password: str):
        self._user = user
        self._password = password

    def _load_sent_ids(self) -> dict:
        if SENT_IDS_FILE.exists():
            try:
                return json.loads(SENT_IDS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _load_seen_uids(self) -> set:
        if SEEN_UIDS_FILE.exists():
            return set(SEEN_UIDS_FILE.read_text(encoding="utf-8").splitlines())
        return set()

    def _mark_seen(self, uid: str):
        SEEN_UIDS_FILE.parent.mkdir(exist_ok=True)
        with SEEN_UIDS_FILE.open("a", encoding="utf-8") as f:
            f.write(uid + "\n")

    def _trim_seen_uids(self, max_lines: int = 30000):
        """Dosya çok büyüdüyse eski UID'leri temizle (son max_lines satırı koru)."""
        if not SEEN_UIDS_FILE.exists():
            return
        lines = SEEN_UIDS_FILE.read_text(encoding="utf-8").splitlines()
        if len(lines) > max_lines:
            SEEN_UIDS_FILE.write_text("\n".join(lines[-max_lines:]) + "\n", encoding="utf-8")
            logger.debug(f"seen_uids trimmed: {len(lines)} → {max_lines}")

    def _cleanup_inbox(self, days: int = 90):
        """90 günden eski inbox kayıtlarını sil."""
        emails = self._load_inbox_emails()
        if len(emails) < 200:
            return
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cleaned = {k: v for k, v in emails.items() if v.get("received_at", "9999") >= cutoff}
        if len(cleaned) < len(emails):
            INBOX_EMAILS_FILE.write_text(
                json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info(f"Inbox cleanup: {len(emails) - len(cleaned)} eski kayıt silindi")

    def _load_inbox_emails(self) -> dict:
        if INBOX_EMAILS_FILE.exists():
            try:
                return json.loads(INBOX_EMAILS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_inbox_email(self, reply_id: str, data: dict):
        emails = self._load_inbox_emails()
        emails[reply_id] = data
        INBOX_EMAILS_FILE.parent.mkdir(exist_ok=True)
        tmp = INBOX_EMAILS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(emails, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, INBOX_EMAILS_FILE)

    def _decode_str(self, value: str) -> str:
        if not value:
            return ""
        parts = []
        for part, charset in decode_header(value):
            if isinstance(part, bytes):
                parts.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                parts.append(str(part))
        return "".join(parts)

    def _get_body(self, msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""

    def check_replies(self) -> list[InboxReply]:
        """Gelen kutusunu kontrol et; bizim outreach maillerimize gelen yanıtları döndür."""
        sent_ids = self._load_sent_ids()
        if not sent_ids:
            logger.debug("Henuz gonderilen outreach mail yok, inbox kontrolu atlandi")
            return []

        seen_uids = self._load_seen_uids()
        replies = []

        try:
            with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
                imap.login(self._user, self._password)
                imap.select("INBOX")

                since = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
                _, data = imap.search(None, f"SINCE {since}")
                uids = data[0].split() if data[0] else []

                for uid in uids:
                    uid_str = uid.decode()
                    if uid_str in seen_uids:
                        continue

                    try:
                        _, msg_data = imap.fetch(uid, "(RFC822)")
                    except Exception:
                        continue

                    if not msg_data or not msg_data[0]:
                        self._mark_seen(uid_str)
                        continue

                    raw = msg_data[0][1]
                    msg = email_lib.message_from_bytes(raw)

                    in_reply_to = msg.get("In-Reply-To", "")
                    references = msg.get("References", "")
                    combined = f"{in_reply_to} {references}"

                    matched_id = next((sid for sid in sent_ids if sid in combined), None)
                    if not matched_id:
                        self._mark_seen(uid_str)
                        continue

                    from_header = msg.get("From", "")
                    from_name, from_email_addr = email_lib.utils.parseaddr(from_header)
                    from_name = self._decode_str(from_name) or from_email_addr
                    subject = self._decode_str(msg.get("Subject", ""))
                    body = self._get_body(msg)

                    reply_id = hashlib.md5(f"{uid_str}{from_email_addr}".encode()).hexdigest()[:8]
                    sent_info = sent_ids[matched_id]

                    reply = InboxReply(
                        reply_id=reply_id,
                        uid=uid_str,
                        from_email=from_email_addr,
                        from_name=from_name,
                        subject=subject,
                        body=body[:800],
                        sent_info=sent_info,
                        matched_message_id=matched_id,
                        received_at=datetime.now().isoformat(),
                    )
                    self._save_inbox_email(reply_id, {
                        "from_email": from_email_addr,
                        "from_name": from_name,
                        "subject": subject,
                        "body": body[:800],
                        "sent_info": sent_info,
                        "matched_message_id": matched_id,
                        "received_at": reply.received_at,
                    })
                    self._mark_seen(uid_str)
                    replies.append(reply)
                    logger.info(f"Yanit bulundu: {from_email_addr} [{reply_id}]")

        except imaplib.IMAP4.error as e:
            logger.error(f"Gmail IMAP auth hatasi: {e}")
        except Exception as e:
            logger.error(f"Gmail IMAP hatasi: {e}")

        self._trim_seen_uids()
        self._cleanup_inbox()
        return replies


_reader: GmailReader | None = None


def init_reader(user: str, password: str) -> GmailReader:
    global _reader
    _reader = GmailReader(user, password)
    logger.info(f"Gmail reader hazir: {user}")
    return _reader


def get_reader() -> GmailReader | None:
    return _reader
