"""Instagram işletme profili bulucu — hashtag + lokasyon bazlı lead tarama."""
import asyncio
import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger

_SESSION_FILE = Path("memory/instagram_session.json")
_client = None


def _get_client():
    global _client
    if _client:
        return _client
    try:
        from instagrapi import Client
        from config import settings
        if not settings.instagram_user or not settings.instagram_password:
            return None
        cl = Client()
        cl.delay_range = [3, 8]  # İnsan gibi gecikme (saniye)
        if _SESSION_FILE.exists():
            try:
                cl.load_settings(_SESSION_FILE)
                cl.login(settings.instagram_user, settings.instagram_password)
                logger.info("Instagram: mevcut oturum yüklendi")
            except Exception:
                _SESSION_FILE.unlink(missing_ok=True)
                cl.login(settings.instagram_user, settings.instagram_password)
                cl.dump_settings(_SESSION_FILE)
                logger.info("Instagram: yeni oturum oluşturuldu")
        else:
            cl.login(settings.instagram_user, settings.instagram_password)
            cl.dump_settings(_SESSION_FILE)
            logger.info("Instagram: giriş yapıldı")
        _client = cl
        return cl
    except Exception as e:
        logger.error(f"Instagram giriş hatası: {e}")
        return None


@dataclass
class InstagramLead:
    username: str
    full_name: str = ""
    bio: str = ""
    website: str = ""
    followers: int = 0
    category: str = ""
    sector: str = ""
    location: str = ""
    is_business: bool = False


# Sektör → arama hashtagleri
_SECTOR_HASHTAGS: dict[str, list[str]] = {
    "restoran":     ["restoran", "restaurant", "yemek", "foodphotography"],
    "kafe":         ["cafe", "kahve", "coffeeshop", "kafe"],
    "dis hekimi":   ["disHekimi", "dental", "dentist", "agizSagligi"],
    "klinik":       ["klinik", "clinic", "saglik", "health"],
    "berber":       ["berber", "barbershop", "sac", "hairstyle"],
    "guzellik":     ["guzelliksalonu", "beautysalon", "makyaj", "beauty"],
    "avukat":       ["avukat", "hukuk", "lawyer", "legal"],
    "muhasebe":     ["muhasebe", "mali", "accounting", "finans"],
    "emlak":        ["emlak", "realestate", "satilik", "kiralik"],
    "otel":         ["otel", "hotel", "konaklama", "travel"],
    "oto servis":   ["otoservis", "otomotiv", "araba", "automotive"],
    "spor salonu":  ["gym", "fitness", "spor", "workout"],
    "restaurant":   ["restaurant", "food", "foodie", "instafood"],
    "dental":       ["dental", "dentist", "smile", "teethwhitening"],
    "friseur":      ["friseur", "hairsalon", "hairstylist", "haarschnitt"],
    "zahnarzt":     ["zahnarzt", "dental", "zahnmedizin", "zahnarztpraxis"],
}

_DEFAULT_HASHTAGS = ["isletme", "sirket", "business", "localBusiness"]


def _get_hashtags(sector: str) -> list[str]:
    s = sector.lower().strip()
    for key, tags in _SECTOR_HASHTAGS.items():
        if key in s or s in key:
            return tags
    return _DEFAULT_HASHTAGS


def _score_lead(lead: InstagramLead) -> float:
    """Yüksek puan = daha iyi potansiyel müşteri."""
    score = 0.0
    if not lead.website:
        score += 3.0  # Websitesi yok → asıl hedef
    if lead.is_business:
        score += 2.0
    if 100 <= lead.followers <= 5000:
        score += 2.0  # Küçük-orta işletme
    elif lead.followers < 100:
        score += 0.5  # Çok küçük
    if lead.bio and len(lead.bio) > 20:
        score += 1.0
    return score


async def find_instagram_leads(
    sector: str, location: str, limit: int = 20
) -> list[InstagramLead]:
    """Instagram'dan işletme profili bul — hashtag araması."""
    loop = asyncio.get_running_loop()
    try:
        leads = await asyncio.wait_for(
            loop.run_in_executor(None, _sync_find, sector, location, limit),
            timeout=120.0,
        )
        return leads
    except asyncio.TimeoutError:
        logger.warning(f"Instagram find timeout — {sector}/{location}")
        return []
    except Exception as e:
        logger.error(f"Instagram find hata: {e}")
        return []


def _sync_find(sector: str, location: str, limit: int) -> list[InstagramLead]:
    cl = _get_client()
    if not cl:
        return []

    hashtags = _get_hashtags(sector)
    leads: list[InstagramLead] = []
    seen: set[str] = set()

    # Önceki bulunanları yükle (tekrar gönderme)
    sent_file = Path("memory/instagram_sent.json")
    sent_usernames: set[str] = set()
    if sent_file.exists():
        try:
            data = json.loads(sent_file.read_text(encoding="utf-8"))
            sent_usernames = {v.get("username", "") for v in data.values()}
        except Exception:
            pass

    for tag in hashtags[:2]:  # Max 2 hashtag — rate limit
        try:
            medias = cl.hashtag_medias_recent(tag, amount=30)
            for media in medias:
                user = media.user
                username = user.username
                if username in seen or username in sent_usernames:
                    continue
                seen.add(username)

                # Profil detayı al
                try:
                    info = cl.user_info(user.pk)
                    lead = InstagramLead(
                        username=username,
                        full_name=info.full_name or "",
                        bio=info.biography or "",
                        website=info.external_url or "",
                        followers=info.follower_count or 0,
                        category=info.category or "",
                        sector=sector,
                        location=location,
                        is_business=info.is_business,
                    )
                    if _score_lead(lead) >= 2.0:
                        leads.append(lead)
                    import time
                    time.sleep(random.uniform(2, 5))  # Rate limit
                except Exception:
                    pass

                if len(leads) >= limit:
                    break
        except Exception as e:
            logger.debug(f"Hashtag arama hatası [{tag}]: {e}")
            continue

        if len(leads) >= limit:
            break

    leads.sort(key=_score_lead, reverse=True)
    logger.info(f"Instagram: {len(leads)} lead bulundu — {sector}/{location}")
    return leads
