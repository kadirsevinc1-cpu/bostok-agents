"""Email doğrulama — domain A/MX varlık kontrolü + bilinen geçersiz domain filtresi.
Göndermeden önce çağrılır; False döndürürse mail atılmaz, bounce önlenir.
"""
import re
import socket
from loguru import logger

_SYNTAX_RE = re.compile(
    r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
)

_DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "yopmail.com", "sharklasers.com", "guerrillamailblock.com", "grr.la",
    "guerrillamail.info", "spam4.me", "trashmail.com", "maildrop.cc",
    "dispostable.com", "fakeinbox.com", "tempr.email", "discard.email",
    "mailnesia.com", "mailnull.com", "spamgourmet.com", "trashmail.at",
    "spamfree24.org", "getairmail.com", "filzmail.com", "spamherelots.com",
    "binkmail.com", "mail-temporaire.fr", "spammotel.com", "superrito.com",
}

_GENERIC_INVALID = {
    "example.com", "test.com", "domain.com", "email.com",
    "localhost", "sample.com", "noemail.com", "noreply.com",
}

_domain_cache: dict[str, bool] = {}


def _domain_reachable(domain: str) -> bool:
    """Domain'e DNS çözümlemesi yapılabiliyor mu? (A kaydı veya CNAME)"""
    if domain in _domain_cache:
        return _domain_cache[domain]
    try:
        socket.getaddrinfo(domain, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        _domain_cache[domain] = True
        return True
    except socket.gaierror:
        _domain_cache[domain] = False
        logger.debug(f"Email validator: domain DNS yok — {domain}")
        return False
    except Exception:
        _domain_cache[domain] = True  # Belirsiz hata → geçerli say
        return True


def is_valid(email: str) -> bool:
    """Email adresini doğrula. False dönerse gönderme."""
    if not email:
        return False
    email = email.strip().lower()

    if not _SYNTAX_RE.match(email):
        logger.debug(f"Email syntax geçersiz: {email}")
        return False

    domain = email.split("@", 1)[1]

    if domain in _GENERIC_INVALID:
        logger.debug(f"Email geçersiz domain (generic): {domain}")
        return False

    if domain in _DISPOSABLE_DOMAINS:
        logger.debug(f"Email geçersiz domain (disposable): {domain}")
        return False

    if not _domain_reachable(domain):
        logger.info(f"Email atlandı (domain yok): {email}")
        return False

    return True
