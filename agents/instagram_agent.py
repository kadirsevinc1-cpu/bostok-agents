"""InstagramAgent — profil bul, DM at, içerik paylaş."""
import asyncio
import json
import os
import random
from datetime import datetime, date
from pathlib import Path
from loguru import logger
from agents.base import BaseAgent
from core.message_bus import AgentName, MessageType, Message, bus

_SENT_FILE  = Path("memory/instagram_sent.json")
_POSTS_FILE = Path("memory/instagram_posts.json")

# Günlük DM limiti — ban riskini azaltmak için düşük tut
_DM_DAILY_LIMIT = 25

# Post için hashtagler
_POST_HASHTAGS = (
    "#webdesign #webdeveloper #website #dijitalajans #bostokdev "
    "#webdesigner #responsive #seo #uxdesign #uiux "
    "#websitedesign #onlinebusiness #digitalmarketing #branding"
)

_POST_SECTOR_HASHTAGS: dict[str, str] = {
    "restoran":  "#restoran #restaurant #yemek #foodie",
    "dental":    "#disHekimi #dental #dentist #saglik",
    "avukat":    "#avukat #hukuk #lawyer",
    "emlak":     "#emlak #realestate #satilik",
    "gym":       "#fitness #gym #sporsalonu #workout",
    "berber":    "#berber #barbershop #erkekSac",
    "guzellik":  "#guzellik #beautysalon #makyaj",
    "otel":      "#otel #hotel #tatil #travel",
    "restaurant":"#restaurant #food #instafood #foodphotography",
    "friseur":   "#friseur #hairsalon #hairstyle",
    "zahnarzt":  "#zahnarzt #dental #zahnmedizin",
}

_CAPTIONS = {
    "tr": [
        "Dijital dünyada yerinizi almak için web siteniz hazır mı? 🌐\nMüşterileriniz sizi Google'da buluyor mu?\nBostok.dev ile profesyonel bir web sitesi için bizimle iletişime geçin. 👇\nhttps://bostok.dev",
        "İyi bir web sitesi, 7/24 açık olan en iyi satış temsilcinizdir. 💼\nHenüz web siteniz yoksa, rakipleriniz fırsatı kaçırıyor demektir — siz değil.\nbostok.dev\n",
        "Yeni bir web sitesi, yeni müşteriler demek! 🚀\nÜcretsiz demo için: https://bostok.dev",
    ],
    "en": [
        "Is your business visible online? 🌐\nA professional website is your best salesperson — open 24/7.\nLet's build yours: https://bostok.dev",
        "No website? You're invisible to 90% of your potential customers. 💡\nGet a modern, fast website at bostok.dev",
    ],
    "de": [
        "Ist Ihr Unternehmen online sichtbar? 🌐\nEine professionelle Website ist Ihr bester Verkäufer — 24/7 geöffnet.\nJetzt starten: https://bostok.dev",
        "Ohne Website verpassen Sie 90% Ihrer Kunden. 💡\nModerne Websites bei bostok.dev",
    ],
}

_DM_TEMPLATES = {
    "tr": (
        "Merhaba {name}! 👋\n\n"
        "Profilinizi gördüm — {sector} sektöründe güzel bir işletmeniz var.\n"
        "Web sitenizi inceledim{website_note}.\n\n"
        "Bostok.dev olarak, sektörünüze özel hızlı ve modern web siteleri yapıyoruz. "
        "Ücretsiz demo hazırladım: https://bostok.dev\n\n"
        "Uygun bir zamanda konuşabilir miyiz?"
    ),
    "en": (
        "Hi {name}! 👋\n\n"
        "I came across your profile — great {sector} business!\n"
        "{website_note}\n\n"
        "At Bostok.dev we build fast, modern websites for businesses like yours. "
        "I've prepared a free demo: https://bostok.dev\n\n"
        "Would you have a few minutes to chat?"
    ),
    "de": (
        "Hallo {name}! 👋\n\n"
        "Ich habe Ihr Profil entdeckt — tolles {sector}-Unternehmen!\n"
        "{website_note}\n\n"
        "Bei Bostok.dev erstellen wir schnelle, moderne Websites. "
        "Ich habe eine kostenlose Demo vorbereitet: https://bostok.dev\n\n"
        "Hätten Sie kurz Zeit für ein Gespräch?"
    ),
}


def _build_system() -> str:
    from core.user_profile import get_context
    ctx = get_context("instagram")
    base = """You are the Instagram agent of Bostok.dev.
Write short, genuine, non-spammy Instagram DMs and post captions.
Always in the target language. Max 80 words for DMs."""
    return f"{ctx}\n\n{base}" if ctx else base


class InstagramAgent(BaseAgent):
    name = AgentName.INSTAGRAM
    system_prompt = _build_system()
    max_tokens = 400

    def __init__(self):
        super().__init__()
        self._dm_count_today = 0
        self._dm_date = date.today()
        self._cl = None

    def _get_client(self):
        if not self._cl:
            from integrations.instagram_finder import _get_client
            self._cl = _get_client()
        return self._cl

    def _load_sent(self) -> dict:
        if _SENT_FILE.exists():
            try:
                return json.loads(_SENT_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_sent(self, data: dict):
        _SENT_FILE.parent.mkdir(exist_ok=True)
        tmp = _SENT_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, _SENT_FILE)

    def _reset_daily(self):
        today = date.today()
        if today != self._dm_date:
            self._dm_count_today = 0
            self._dm_date = today

    def _can_dm(self) -> bool:
        self._reset_daily()
        return self._dm_count_today < _DM_DAILY_LIMIT

    async def loop(self):
        # Saatte bir çalış
        self.last_heartbeat = datetime.now()
        await self._run_cycle()
        for _ in range(120):  # 1 saat = 120 × 30s
            if not self.running:
                break
            self.last_heartbeat = datetime.now()
            await asyncio.sleep(30)

    async def _run_cycle(self):
        cl = await asyncio.get_running_loop().run_in_executor(None, self._get_client)
        if not cl:
            logger.info("Instagram: hesap yapılandırılmamış, atlanıyor")
            return

        from core.campaigns import CAMPAIGNS
        import random as _rand

        # Rastgele bir kampanya seç
        camp = _rand.choice(CAMPAIGNS)
        sector = camp["sector"]
        location = _rand.choice(camp["locations"])
        lang = camp["langs"][0] if camp["langs"] else "tr"

        # 1. Lead bul
        from integrations.instagram_finder import find_instagram_leads
        leads = await find_instagram_leads(sector, location, limit=15)

        # 2. DM at (limitli)
        if leads and self._can_dm():
            await self._send_dms(cl, leads, sector, lang)

        # 3. Post paylaş (günde max 2)
        await self._maybe_post(cl, sector, lang)

    async def _send_dms(self, cl, leads, sector: str, lang: str):
        sent_data = self._load_sent()
        loop = asyncio.get_running_loop()

        for lead in leads:
            if not self._can_dm():
                break
            if lead.username in sent_data:
                continue

            try:
                msg = await self._write_dm(lead, sector, lang)
                ok = await loop.run_in_executor(
                    None, self._sync_send_dm, cl, lead.username, msg
                )
                if ok:
                    sent_data[lead.username] = {
                        "username": lead.username,
                        "sector": sector,
                        "sent_at": datetime.now().isoformat(),
                        "lang": lang,
                    }
                    self._save_sent(sent_data)
                    self._dm_count_today += 1
                    self.last_heartbeat = datetime.now()
                    logger.info(f"Instagram DM: @{lead.username} ({self._dm_count_today}/{_DM_DAILY_LIMIT})")
                    await bus.send(Message(
                        sender=AgentName.INSTAGRAM,
                        receiver=AgentName.SYSTEM,
                        type=MessageType.USER_NOTIFY,
                        content=f"📸 Instagram DM: @{lead.username} ({sector}/{lead.location})",
                    ))
                    # İnsan gibi gecikme
                    delay = random.uniform(180, 480)  # 3-8 dk
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.debug(f"DM gönderilemedi @{lead.username}: {e}")

    def _sync_send_dm(self, cl, username: str, message: str) -> bool:
        try:
            user_id = cl.user_id_from_username(username)
            cl.direct_send(message, [user_id])
            return True
        except Exception as e:
            logger.debug(f"DM send error: {e}")
            return False

    async def _write_dm(self, lead, sector: str, lang: str) -> str:
        name = lead.full_name.split()[0] if lead.full_name else lead.username
        if lead.website:
            website_note = {
                "tr": "web siteniz var ama geliştirilebilir",
                "en": "I noticed your website could use some improvements",
                "de": "Ich habe gesehen, Ihre Website könnte verbessert werden",
            }.get(lang, "I noticed your website could use some improvements")
        else:
            website_note = {
                "tr": "ama web siteniz yok",
                "en": "but I noticed you don't have a website yet",
                "de": "aber ich habe bemerkt, dass Sie noch keine Website haben",
            }.get(lang, "but I noticed you don't have a website yet")

        template = _DM_TEMPLATES.get(lang, _DM_TEMPLATES["en"])
        base_msg = template.format(
            name=name, sector=sector, website_note=website_note
        )

        # LLM ile kişiselleştir (biyografi varsa)
        if lead.bio and len(lead.bio) > 15:
            prompt = (
                f"Personalize this Instagram DM slightly using this bio: '{lead.bio[:100]}'\n"
                f"Keep the same language and structure. Max 80 words.\n\n"
                f"Original:\n{base_msg}"
            )
            try:
                personalized = await self.ask(prompt)
                if personalized and len(personalized.strip()) > 30:
                    return personalized.strip()
            except Exception:
                pass

        return base_msg

    async def _maybe_post(self, cl, sector: str, lang: str):
        """Günde max 2 post paylaş."""
        posts = {}
        if _POSTS_FILE.exists():
            try:
                posts = json.loads(_POSTS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

        today_str = date.today().isoformat()
        today_posts = posts.get(today_str, 0)
        if today_posts >= 2:
            return

        try:
            image_path = await self._get_post_image(sector)
            if not image_path:
                return
            caption = await self._write_caption(sector, lang)
            loop = asyncio.get_running_loop()
            ok = await loop.run_in_executor(
                None, self._sync_post, cl, image_path, caption
            )
            if ok:
                posts[today_str] = today_posts + 1
                _POSTS_FILE.parent.mkdir(exist_ok=True)
                _POSTS_FILE.write_text(
                    json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                logger.info(f"Instagram post paylaşıldı ({sector})")
                await bus.send(Message(
                    sender=AgentName.INSTAGRAM,
                    receiver=AgentName.SYSTEM,
                    type=MessageType.USER_NOTIFY,
                    content=f"📸 Instagram post paylaşıldı: {sector}",
                ))
        except Exception as e:
            logger.debug(f"Post paylaşma hatası: {e}")

    async def _get_post_image(self, sector: str) -> str | None:
        """Pexels'tan sektöre uygun görsel indir."""
        try:
            from integrations.pexels_photos import get_sector_photo
            from config import settings as _cfg
            if not _cfg.pexels_api_key:
                return None

            _SECTOR_CAT = {
                "restoran": "food", "restaurant": "food", "kafe": "coffee",
                "dis hekimi": "health", "dental": "health", "zahnarzt": "health",
                "berber": "barber", "guzellik": "beauty", "friseur": "hair",
                "avukat": "office", "muhasebe": "office", "emlak": "house",
                "otel": "hotel", "gym": "fitness", "spor salonu": "fitness",
            }
            cat = next((v for k, v in _SECTOR_CAT.items() if k in sector.lower()), "business")
            photo_url = await get_sector_photo(cat, _cfg.pexels_api_key)
            if not photo_url:
                return None

            # Görseli indir
            import aiohttp
            tmp_path = Path("memory/ig_post_tmp.jpg")
            async with aiohttp.ClientSession() as s:
                async with s.get(photo_url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status == 200:
                        tmp_path.write_bytes(await r.read())
                        return str(tmp_path)
        except Exception as e:
            logger.debug(f"Post görsel hatası: {e}")
        return None

    def _sync_post(self, cl, image_path: str, caption: str) -> bool:
        try:
            cl.photo_upload(image_path, caption)
            return True
        except Exception as e:
            logger.debug(f"Photo upload error: {e}")
            return False

    async def _write_caption(self, sector: str, lang: str) -> str:
        sector_tag = _POST_SECTOR_HASHTAGS.get(sector.lower(), "")
        captions = _CAPTIONS.get(lang, _CAPTIONS["en"])
        base = random.choice(captions)
        full = f"{base}\n\n{sector_tag}\n{_POST_HASHTAGS}"

        prompt = (
            f"Write a short Instagram caption in {lang} for a web design agency post "
            f"targeting {sector} businesses. Max 60 words. "
            f"End with: https://bostok.dev\n"
            f"Then add these hashtags exactly: {sector_tag} {_POST_HASHTAGS}"
        )
        try:
            caption = await self.ask(prompt)
            if caption and len(caption.strip()) > 20:
                return caption.strip()
        except Exception:
            pass
        return full
