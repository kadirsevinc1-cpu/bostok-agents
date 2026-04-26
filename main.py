"""
Bostok Agent Köyü — Ana başlatıcı.
Kullanım:
  python main.py                          # demo görevi
  python main.py "Müşteri talebi buraya" # özel görev
"""
import asyncio
import sys
from loguru import logger
from core.message_bus import bus, AgentName, MessageType, Message
from core.budget import budget
from agents.manager import ManagerAgent
from agents.analyst import AnalystAgent
from agents.marketing import MarketingAgent
from agents.quote import QuoteAgent
from agents.content import ContentAgent
from agents.designer import DesignerAgent
from agents.developer import DeveloperAgent
from agents.qa import QAAgent
from agents.deploy import DeployAgent
from agents.inbox_watcher import InboxWatcherAgent
from agents.followup import FollowupAgent
from agents.knowledge_agent import KnowledgeAgent
from integrations.telegram import init_bot, get_bot
from integrations.gmail import init_gmail
from integrations.gmail_reader import init_reader
from integrations.netlify import init_netlify


def setup_logging():
    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")
    logger.add("memory/bostok.log", rotation="10 MB", level="DEBUG")


async def budget_monitor():
    while True:
        await asyncio.sleep(300)
        report = budget.report()
        logger.info(f"\n{report}")
        if budget.is_blocked():
            logger.error("BUTCE LIMITI ASILDI!")
            bot = get_bot()
            if bot:
                await bot.send("Gunluk token limiti asildi. Sistem durduruldu.")
            await bus.send(Message(
                sender=AgentName.SYSTEM, receiver=AgentName.MANAGER,
                type=MessageType.BUDGET_ALERT,
                content="Gunluk token limiti asildi.",
            ))


CAMPAIGNS = [
    # ── Türkiye — Yeme & İçme ─────────────────────────────────────
    {"sector": "restoran",         "locations": ["Istanbul", "Ankara", "Izmir", "Antalya", "Bursa", "Gaziantep", "Adana", "Mersin", "Kayseri", "Samsun", "Trabzon", "Denizli", "Malatya", "Sanliurfa", "Erzurum", "Tekirdag", "Edirne", "Sakarya", "Ordu", "Diyarbakir", "Canakkale", "Rize", "Kahramanmaras", "Corum"], "langs": ["tr"]},
    {"sector": "kafe",             "locations": ["Istanbul", "Ankara", "Izmir", "Eskisehir", "Samsun", "Trabzon", "Denizli", "Kayseri", "Adana", "Tekirdag", "Edirne", "Canakkale", "Ordu", "Rize"], "langs": ["tr"]},
    {"sector": "pastane",          "locations": ["Istanbul", "Ankara", "Bursa", "Konya", "Adana", "Samsun", "Trabzon", "Kayseri", "Tekirdag", "Sakarya", "Ordu"], "langs": ["tr"]},
    {"sector": "catering",         "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Mersin", "Samsun", "Tekirdag", "Sakarya", "Diyarbakir"], "langs": ["tr"]},

    # ── Türkiye — Sağlık ──────────────────────────────────────────
    {"sector": "dis hekimi",       "locations": ["Istanbul", "Ankara", "Izmir", "Konya", "Antalya", "Adana", "Mersin", "Kayseri", "Samsun", "Denizli", "Hatay", "Trabzon", "Malatya", "Tekirdag", "Edirne", "Sakarya", "Ordu", "Diyarbakir", "Kahramanmaras", "Corum"], "langs": ["tr"]},
    {"sector": "eczane",           "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Mersin", "Samsun", "Kayseri", "Tekirdag", "Sakarya", "Diyarbakir"], "langs": ["tr"]},
    {"sector": "veteriner",        "locations": ["Istanbul", "Ankara", "Izmir", "Antalya", "Adana", "Samsun", "Denizli", "Tekirdag", "Sakarya", "Canakkale"], "langs": ["tr"]},
    {"sector": "spor salonu",      "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana", "Mersin", "Kayseri", "Samsun", "Tekirdag", "Sakarya", "Diyarbakir"], "langs": ["tr"]},
    {"sector": "psikolog",         "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Samsun", "Kayseri", "Tekirdag", "Sakarya", "Diyarbakir"], "langs": ["tr"]},
    {"sector": "fizyoterapist",    "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Samsun", "Bursa", "Tekirdag", "Sakarya", "Kahramanmaras"], "langs": ["tr"]},

    # ── Türkiye — Hukuk & Finans ──────────────────────────────────
    {"sector": "avukat",           "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Mersin", "Kayseri", "Samsun", "Erzurum", "Hatay", "Malatya", "Sanliurfa", "Tekirdag", "Sakarya", "Diyarbakir", "Kahramanmaras", "Corum"], "langs": ["tr"]},
    {"sector": "muhasebe",         "locations": ["Istanbul", "Ankara", "Izmir", "Kocaeli", "Adana", "Mersin", "Samsun", "Kayseri", "Denizli", "Tekirdag", "Sakarya", "Diyarbakir", "Corum"], "langs": ["tr"]},
    {"sector": "sigorta",          "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Mersin", "Samsun", "Kayseri", "Tekirdag", "Sakarya", "Diyarbakir"], "langs": ["tr"]},
    {"sector": "mali musavir",     "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Samsun", "Kayseri", "Tekirdag", "Sakarya", "Diyarbakir"], "langs": ["tr"]},

    # ── Türkiye — Güzellik & Bakım ────────────────────────────────
    {"sector": "guzellik salonu",  "locations": ["Istanbul", "Ankara", "Antalya", "Bursa", "Izmir", "Adana", "Mersin", "Kayseri", "Samsun", "Denizli", "Trabzon", "Hatay", "Tekirdag", "Edirne", "Sakarya", "Ordu", "Diyarbakir", "Canakkale"], "langs": ["tr"]},
    {"sector": "berber",           "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Mersin", "Samsun", "Trabzon", "Denizli", "Kayseri", "Tekirdag", "Edirne", "Kirklareli", "Sakarya", "Ordu", "Diyarbakir", "Canakkale", "Rize", "Kahramanmaras", "Corum"], "langs": ["tr"]},
    {"sector": "tirnak salonu",    "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Samsun", "Kayseri", "Tekirdag", "Sakarya", "Diyarbakir"], "langs": ["tr"]},
    {"sector": "spa",              "locations": ["Istanbul", "Antalya", "Bodrum", "Alanya", "Trabzon", "Mersin", "Canakkale", "Edirne", "Rize"], "langs": ["tr", "en"]},

    # ── Türkiye — Emlak & İnşaat ──────────────────────────────────
    {"sector": "emlakci",          "locations": ["Istanbul", "Ankara", "Alanya", "Bodrum", "Izmir", "Adana", "Mersin", "Samsun", "Denizli", "Trabzon", "Kayseri", "Tekirdag", "Edirne", "Sakarya", "Canakkale", "Diyarbakir"], "langs": ["tr"]},
    {"sector": "insaat",           "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Kayseri", "Gaziantep", "Tekirdag", "Sakarya", "Diyarbakir", "Kahramanmaras"], "langs": ["tr"]},
    {"sector": "tadilat",          "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Samsun", "Kayseri", "Bursa", "Tekirdag", "Sakarya", "Diyarbakir"], "langs": ["tr"]},
    {"sector": "temizlik sirketi", "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Mersin", "Kayseri", "Tekirdag", "Sakarya", "Diyarbakir"], "langs": ["tr"]},
    {"sector": "nakliyat",         "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Mersin", "Tekirdag", "Sakarya", "Diyarbakir"], "langs": ["tr"]},
    {"sector": "elektrikci",       "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Samsun", "Kayseri", "Bursa", "Tekirdag", "Sakarya", "Kahramanmaras", "Corum"], "langs": ["tr"]},

    # ── Türkiye — Otomotiv ────────────────────────────────────────
    {"sector": "oto servis",       "locations": ["Istanbul", "Ankara", "Bursa", "Kocaeli", "Izmir", "Adana", "Mersin", "Samsun", "Gaziantep", "Denizli", "Kayseri", "Tekirdag", "Sakarya", "Diyarbakir", "Kahramanmaras", "Corum"], "langs": ["tr"]},
    {"sector": "oto yikama",       "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Mersin", "Tekirdag", "Sakarya", "Diyarbakir", "Corum"], "langs": ["tr"]},
    {"sector": "lastikci",         "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Samsun", "Kayseri", "Bursa", "Tekirdag", "Sakarya", "Diyarbakir", "Kahramanmaras"], "langs": ["tr"]},
    {"sector": "oto kiralama",     "locations": ["Istanbul", "Antalya", "Izmir", "Bodrum", "Trabzon", "Mersin", "Alanya", "Canakkale", "Edirne"], "langs": ["tr", "en"]},

    # ── Türkiye — Eğitim ──────────────────────────────────────────
    {"sector": "ozel okul",        "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Samsun", "Kayseri", "Bursa", "Tekirdag", "Sakarya", "Diyarbakir"], "langs": ["tr"]},
    {"sector": "dil kursu",        "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Trabzon", "Kayseri", "Tekirdag", "Sakarya", "Canakkale", "Edirne"], "langs": ["tr"]},
    {"sector": "etut merkezi",     "locations": ["Istanbul", "Ankara", "Izmir", "Konya", "Bursa", "Adana", "Samsun", "Kayseri", "Trabzon", "Tekirdag", "Sakarya", "Diyarbakir", "Corum"], "langs": ["tr"]},
    {"sector": "surucu kursu",     "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Mersin", "Kayseri", "Tekirdag", "Edirne", "Kirklareli", "Sakarya", "Diyarbakir"], "langs": ["tr"]},
    {"sector": "dans okulu",       "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Samsun", "Tekirdag", "Sakarya"], "langs": ["tr"]},
    {"sector": "kres",             "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Kayseri", "Mersin", "Tekirdag", "Sakarya", "Diyarbakir", "Corum"], "langs": ["tr"]},

    # ── Türkiye — Konaklama ───────────────────────────────────────
    {"sector": "otel",             "locations": ["Antalya", "Cappadocia", "Bodrum", "Alanya", "Kusadasi", "Trabzon", "Erzurum", "Samsun", "Mersin", "Adana", "Hatay", "Edirne", "Canakkale", "Rize", "Ordu"], "langs": ["tr", "en"]},
    {"sector": "pansiyon",         "locations": ["Cappadocia", "Bodrum", "Alanya", "Safranbolu", "Trabzon", "Artvin", "Amasya", "Mardin", "Edirne", "Canakkale", "Rize", "Ordu"], "langs": ["tr", "en"]},
    {"sector": "apart otel",       "locations": ["Istanbul", "Ankara", "Antalya", "Izmir", "Adana", "Samsun", "Mersin", "Tekirdag", "Sakarya", "Diyarbakir"], "langs": ["tr"]},

    # ── Türkiye — Mağaza & Hizmet ─────────────────────────────────
    {"sector": "cicekci",          "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Kayseri", "Trabzon"], "langs": ["tr"]},
    {"sector": "optik",            "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Samsun", "Kayseri"],   "langs": ["tr"]},
    {"sector": "pet shop",         "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Samsun", "Bursa"],     "langs": ["tr"]},
    {"sector": "kuru temizleme",   "locations": ["Istanbul", "Ankara", "Izmir", "Adana", "Samsun", "Kayseri", "Bursa"], "langs": ["tr"]},
    {"sector": "fotograf",         "locations": ["Istanbul", "Ankara", "Izmir", "Antalya", "Samsun", "Trabzon", "Kayseri"], "langs": ["tr"]},

    # ── Türkiye — Sanayi ──────────────────────────────────────────
    {"sector": "sanayi",           "locations": ["Istanbul", "Bursa", "Kocaeli", "Ankara", "Izmir", "Konya", "Tekirdag", "Sakarya", "Kahramanmaras"], "langs": ["tr"]},
    {"sector": "imalat",           "locations": ["Bursa", "Kocaeli", "Gaziantep", "Konya", "Eskisehir", "Tekirdag", "Sakarya", "Kahramanmaras", "Corum"], "langs": ["tr"]},
    {"sector": "tekstil",          "locations": ["Istanbul", "Bursa", "Denizli", "Gaziantep", "Tekirdag"],        "langs": ["tr", "en"]},
    {"sector": "depo ve lojistik", "locations": ["Istanbul", "Ankara", "Izmir", "Kocaeli", "Tekirdag", "Sakarya"], "langs": ["tr"]},

    # ── Almanya & Avusturya & İsviçre ─────────────────────────────
    {"sector": "restaurant",       "locations": ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Stuttgart", "Nuremberg", "Dresden", "Leipzig", "Bremen", "Hannover", "Dortmund"], "langs": ["tr", "de"]},
    {"sector": "friseur",          "locations": ["Berlin", "Hamburg", "Dusseldorf", "Frankfurt", "Stuttgart", "Nuremberg", "Leipzig", "Bremen", "Hannover", "Dortmund"], "langs": ["tr", "de"]},
    {"sector": "autohaus",         "locations": ["Frankfurt", "Stuttgart", "Munich", "Cologne", "Nuremberg", "Hannover", "Dortmund"], "langs": ["de"]},
    {"sector": "immobilienmakler", "locations": ["Berlin", "Hamburg", "Munich", "Frankfurt", "Leipzig", "Dresden", "Hannover", "Nuremberg"], "langs": ["de"]},
    {"sector": "zahnarzt",         "locations": ["Vienna", "Zurich", "Bern", "Graz", "Berlin", "Nuremberg", "Dresden", "Leipzig", "Hannover"], "langs": ["de"]},
    {"sector": "rechtsanwalt",     "locations": ["Berlin", "Hamburg", "Munich", "Frankfurt", "Nuremberg", "Leipzig", "Dresden", "Hannover", "Dortmund"], "langs": ["de"]},
    {"sector": "steuerberater",    "locations": ["Berlin", "Hamburg", "Munich", "Cologne", "Nuremberg", "Leipzig", "Hannover", "Dortmund", "Frankfurt"], "langs": ["de"]},
    {"sector": "fitnessstudio",    "locations": ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Nuremberg", "Leipzig", "Hannover", "Dortmund"], "langs": ["de"]},
    {"sector": "fahrschule",       "locations": ["Berlin", "Hamburg", "Munich", "Frankfurt", "Nuremberg", "Leipzig", "Hannover", "Cologne"], "langs": ["de"]},
    {"sector": "tierarzt",         "locations": ["Berlin", "Hamburg", "Munich", "Vienna", "Nuremberg", "Leipzig", "Frankfurt", "Hannover"], "langs": ["de"]},
    {"sector": "manufacturing",    "locations": ["Stuttgart", "Munich", "Frankfurt", "Dusseldorf", "Nuremberg", "Hannover", "Dortmund", "Leipzig"], "langs": ["de"]},

    # ── Hollanda & Belçika ────────────────────────────────────────
    {"sector": "restaurant",       "locations": ["Amsterdam", "Rotterdam", "The Hague", "Brussels", "Antwerp"],   "langs": ["en", "nl"]},
    {"sector": "beauty salon",     "locations": ["Amsterdam", "Rotterdam", "Ghent", "Brussels"],                  "langs": ["en"]},
    {"sector": "dental clinic",    "locations": ["Amsterdam", "Rotterdam", "Brussels"],                           "langs": ["en"]},
    {"sector": "real estate",      "locations": ["Amsterdam", "Rotterdam", "Brussels"],                           "langs": ["en", "nl"]},

    # ── İngiltere ─────────────────────────────────────────────────
    {"sector": "restaurant",       "locations": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool", "Sheffield", "Bristol", "Newcastle", "Nottingham", "Edinburgh", "Cardiff"], "langs": ["en"]},
    {"sector": "solicitor",        "locations": ["London", "Birmingham", "Manchester", "Leeds", "Liverpool", "Sheffield", "Bristol", "Newcastle", "Nottingham", "Edinburgh"], "langs": ["en"]},
    {"sector": "estate agent",     "locations": ["London", "Manchester", "Bristol", "Edinburgh", "Liverpool", "Sheffield", "Newcastle", "Leeds", "Nottingham", "Cardiff"], "langs": ["en"]},
    {"sector": "dental clinic",    "locations": ["London", "Birmingham", "Leeds", "Manchester", "Liverpool", "Sheffield", "Bristol", "Newcastle", "Nottingham"], "langs": ["en"]},
    {"sector": "gym",              "locations": ["London", "Manchester", "Birmingham", "Leeds", "Liverpool", "Sheffield", "Bristol", "Newcastle", "Nottingham"], "langs": ["en"]},
    {"sector": "accountant",       "locations": ["London", "Manchester", "Birmingham", "Liverpool", "Sheffield", "Bristol", "Newcastle", "Leeds", "Nottingham"], "langs": ["en"]},
    {"sector": "cleaning service", "locations": ["London", "Manchester", "Birmingham", "Leeds", "Liverpool", "Sheffield", "Bristol", "Newcastle", "Cardiff"], "langs": ["en"]},
    {"sector": "driving school",   "locations": ["London", "Birmingham", "Manchester", "Liverpool", "Sheffield", "Bristol", "Newcastle"], "langs": ["en"]},
    {"sector": "barber shop",      "locations": ["London", "Manchester", "Birmingham", "Liverpool", "Sheffield", "Bristol", "Newcastle", "Nottingham"], "langs": ["en"]},
    {"sector": "florist",          "locations": ["London", "Manchester", "Edinburgh", "Liverpool", "Sheffield", "Bristol", "Newcastle"], "langs": ["en"]},

    # ── Amerika (USA) ─────────────────────────────────────────────
    {"sector": "restaurant",       "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Miami", "Phoenix", "Dallas", "San Diego", "San Antonio", "San Jose"], "langs": ["en"]},
    {"sector": "law firm",         "locations": ["New York", "Los Angeles", "Miami", "Chicago", "Houston", "Atlanta", "Washington DC", "Boston", "Seattle"],             "langs": ["en"]},
    {"sector": "real estate",      "locations": ["Miami", "Dallas", "Phoenix", "Las Vegas", "Austin", "Denver", "Nashville", "Orlando", "Tampa", "Charlotte"],          "langs": ["en"]},
    {"sector": "dental office",    "locations": ["New York", "Chicago", "Houston", "Phoenix", "Los Angeles", "San Diego", "Atlanta", "Miami"],                          "langs": ["en"]},
    {"sector": "beauty salon",     "locations": ["New York", "Los Angeles", "Atlanta", "Dallas", "Houston", "Chicago", "Miami", "Las Vegas"],                           "langs": ["en"]},
    {"sector": "auto repair shop", "locations": ["Houston", "Dallas", "Phoenix", "Los Angeles", "Chicago", "San Antonio"],                                              "langs": ["en"]},
    {"sector": "accounting firm",  "locations": ["New York", "Chicago", "Los Angeles", "Miami", "Houston", "Boston"],                                                   "langs": ["en"]},
    {"sector": "hotel",            "locations": ["Las Vegas", "Miami", "New York", "Orlando", "Los Angeles", "New Orleans", "Nashville"],                               "langs": ["en"]},
    {"sector": "gym",              "locations": ["New York", "Los Angeles", "Chicago", "Miami", "Houston", "Dallas"],                                                   "langs": ["en"]},
    {"sector": "pharmacy",         "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],                                                           "langs": ["en"]},
    {"sector": "vet clinic",       "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Dallas"],                                                            "langs": ["en"]},
    {"sector": "insurance agency", "locations": ["New York", "Los Angeles", "Miami", "Chicago", "Houston"],                                                             "langs": ["en"]},
    {"sector": "tutoring center",  "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Atlanta"],                                                           "langs": ["en"]},
    {"sector": "cleaning service", "locations": ["New York", "Los Angeles", "Miami", "Chicago", "Houston", "Dallas"],                                                   "langs": ["en"]},
    {"sector": "barber shop",      "locations": ["New York", "Los Angeles", "Atlanta", "Miami", "Chicago"],                                                             "langs": ["en"]},
    {"sector": "florist",          "locations": ["New York", "Los Angeles", "Chicago", "Miami"],                                                                        "langs": ["en"]},
    {"sector": "pet shop",         "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Miami"],                                                             "langs": ["en"]},
    {"sector": "manufacturing",    "locations": ["Detroit", "Chicago", "Houston", "Dallas", "Los Angeles"],                                                             "langs": ["en"]},

    # ── Kanada ────────────────────────────────────────────────────
    {"sector": "restaurant",       "locations": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa", "Edmonton"], "langs": ["en"]},
    {"sector": "real estate",      "locations": ["Toronto", "Vancouver", "Calgary", "Montreal"],                  "langs": ["en"]},
    {"sector": "dental clinic",    "locations": ["Toronto", "Vancouver", "Calgary"],                              "langs": ["en"]},
    {"sector": "gym",              "locations": ["Toronto", "Vancouver", "Calgary", "Montreal"],                  "langs": ["en"]},
    {"sector": "cleaning service", "locations": ["Toronto", "Vancouver", "Calgary"],                              "langs": ["en"]},

    # ── Avustralya & Yeni Zelanda ─────────────────────────────────
    {"sector": "restaurant",       "locations": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Auckland"], "langs": ["en"]},
    {"sector": "real estate",      "locations": ["Sydney", "Melbourne", "Brisbane", "Gold Coast"],                "langs": ["en"]},
    {"sector": "dental clinic",    "locations": ["Sydney", "Melbourne", "Brisbane"],                              "langs": ["en"]},
    {"sector": "gym",              "locations": ["Sydney", "Melbourne", "Brisbane"],                              "langs": ["en"]},
    {"sector": "beauty salon",     "locations": ["Sydney", "Melbourne", "Brisbane", "Gold Coast"],                "langs": ["en"]},

    # ── Orta Doğu — BAE ───────────────────────────────────────────
    {"sector": "restaurant",       "locations": ["Dubai", "Abu Dhabi", "Sharjah", "Ajman"],                      "langs": ["en"]},
    {"sector": "real estate",      "locations": ["Dubai", "Abu Dhabi", "Sharjah"],                               "langs": ["en"]},
    {"sector": "beauty salon",     "locations": ["Dubai", "Abu Dhabi", "Sharjah"],                               "langs": ["en"]},
    {"sector": "dental clinic",    "locations": ["Dubai", "Abu Dhabi"],                                          "langs": ["en"]},
    {"sector": "law firm",         "locations": ["Dubai", "Abu Dhabi"],                                          "langs": ["en"]},
    {"sector": "gym",              "locations": ["Dubai", "Abu Dhabi", "Sharjah"],                               "langs": ["en"]},
    {"sector": "hotel",            "locations": ["Dubai", "Abu Dhabi"],                                          "langs": ["en"]},
    {"sector": "manufacturing",    "locations": ["Dubai", "Abu Dhabi", "Sharjah"],                               "langs": ["en"]},

    # ── Orta Doğu — Suudi Arabistan ───────────────────────────────
    {"sector": "restaurant",       "locations": ["Riyadh", "Jeddah", "Mecca", "Medina", "Dammam"],               "langs": ["en"]},
    {"sector": "real estate",      "locations": ["Riyadh", "Jeddah", "Dammam"],                                  "langs": ["en"]},
    {"sector": "beauty salon",     "locations": ["Riyadh", "Jeddah"],                                            "langs": ["en"]},
    {"sector": "hotel",            "locations": ["Riyadh", "Jeddah", "Mecca"],                                   "langs": ["en"]},
    {"sector": "dental clinic",    "locations": ["Riyadh", "Jeddah", "Dammam"],                                  "langs": ["en"]},
    {"sector": "gym",              "locations": ["Riyadh", "Jeddah"],                                            "langs": ["en"]},

    # ── Orta Doğu — Diğer ────────────────────────────────────────
    {"sector": "restaurant",       "locations": ["Doha", "Kuwait City", "Manama", "Muscat", "Amman", "Beirut"],  "langs": ["en"]},
    {"sector": "real estate",      "locations": ["Doha", "Kuwait City", "Muscat", "Amman"],                      "langs": ["en"]},
    {"sector": "hotel",            "locations": ["Doha", "Muscat", "Amman", "Beirut"],                           "langs": ["en"]},
    {"sector": "beauty salon",     "locations": ["Doha", "Kuwait City", "Muscat"],                               "langs": ["en"]},
    {"sector": "dental clinic",    "locations": ["Doha", "Kuwait City", "Muscat"],                               "langs": ["en"]},

    # ── İskandinav ────────────────────────────────────────────────
    {"sector": "restaurant",       "locations": ["Stockholm", "Oslo", "Copenhagen", "Helsinki"],                  "langs": ["en"]},
    {"sector": "tandlakare",       "locations": ["Stockholm", "Gothenburg", "Malmo"],                             "langs": ["en"]},
    {"sector": "gym",              "locations": ["Stockholm", "Oslo", "Copenhagen"],                              "langs": ["en"]},
    {"sector": "real estate",      "locations": ["Stockholm", "Oslo", "Copenhagen"],                              "langs": ["en"]},
    {"sector": "beauty salon",     "locations": ["Stockholm", "Oslo", "Copenhagen", "Helsinki"],                  "langs": ["en"]},

    # ── Fransa & İspanya & İtalya ─────────────────────────────────
    {"sector": "restaurant",       "locations": ["Paris", "Lyon", "Madrid", "Barcelona", "Rome", "Milan"],        "langs": ["en"]},
    {"sector": "agence immobiliere","locations": ["Paris", "Nice", "Bordeaux"],                                   "langs": ["en", "fr"]},
    {"sector": "beauty salon",     "locations": ["Paris", "Madrid", "Barcelona", "Rome", "Milan"],                "langs": ["en"]},
    {"sector": "dental clinic",    "locations": ["Paris", "Madrid", "Barcelona", "Rome"],                         "langs": ["en"]},
    {"sector": "hotel",            "locations": ["Paris", "Nice", "Barcelona", "Rome", "Florence"],               "langs": ["en"]},

    # ── Güney & Doğu Asya ─────────────────────────────────────────
    {"sector": "restaurant",       "locations": ["Singapore", "Kuala Lumpur", "Jakarta", "Bangkok", "Mumbai", "Delhi"], "langs": ["en"]},
    {"sector": "real estate",      "locations": ["Singapore", "Kuala Lumpur", "Bangkok", "Mumbai"],               "langs": ["en"]},
    {"sector": "hotel",            "locations": ["Singapore", "Bangkok", "Bali", "Phuket"],                       "langs": ["en"]},
    {"sector": "dental clinic",    "locations": ["Singapore", "Kuala Lumpur", "Bangkok"],                         "langs": ["en"]},
    {"sector": "beauty salon",     "locations": ["Singapore", "Kuala Lumpur", "Bangkok"],                         "langs": ["en"]},
    {"sector": "manufacturing",    "locations": ["Singapore", "Kuala Lumpur", "Jakarta", "Bangkok"],              "langs": ["en"]},
]


async def marketing_scheduler():
    """Her 4 saatte bir farkli sektörde pazarlama kampanyası baslatir."""
    await asyncio.sleep(45)  # Sistem tam baslasin
    logger.info("Pazarlama zamanlayici basladi")

    campaign_idx = 0
    while True:
        campaign = CAMPAIGNS[campaign_idx % len(CAMPAIGNS)]
        campaign_idx += 1
        total = len(campaign["locations"])

        logger.info(
            f"[Kampanya {campaign_idx}/{len(CAMPAIGNS)}] "
            f"{campaign['sector'].upper()} — {total} lokasyon: "
            f"{', '.join(campaign['locations'][:4])}"
            + (f" ...+{total - 4}" if total > 4 else "")
        )

        for loc_idx, location in enumerate(campaign["locations"], 1):
            logger.info(
                f"  [{loc_idx}/{total}] {campaign['sector']} — {location}"
            )
            await bus.send(Message(
                sender=AgentName.SYSTEM,
                receiver=AgentName.MARKETING,
                type=MessageType.TASK,
                content=f"{location}'daki {campaign['sector']} isletmelerine web sitesi teklifi hazirla",
                metadata={
                    "sector": campaign["sector"],
                    "location": location,
                    "languages": campaign["langs"],
                    "send_emails": True,
                },
            ))
            await asyncio.sleep(10)  # Kampanyalar arasi bekleme

        logger.info(f"[Kampanya tamamlandi] {campaign['sector']} — 1 saat bekleniyor")
        await asyncio.sleep(3600)  # 1 saat


async def notify_handler(msg: Message):
    """Bildirimleri hem konsola bas hem Telegram'a gönder."""
    if msg.type != MessageType.USER_NOTIFY:
        return

    # Konsola yaz
    print(f"\n{'='*60}")
    print(f"BILDIRIM [{msg.sender.value}]:")
    print(msg.content)
    print('='*60)

    # Telegram'a gönder
    bot = get_bot()
    if not bot:
        return

    requires_approval = msg.metadata.get("requires_approval", False)

    if requires_approval:
        # Onay butonu ile gönder
        import uuid
        approval_id = uuid.uuid4().hex[:8]
        approved = await bot.request_approval(approval_id, msg.content)
        if approved:
            await bus.send(Message(
                sender=AgentName.SYSTEM, receiver=AgentName.MANAGER,
                type=MessageType.APPROVAL, content="Kullanici onayi alindi.",
            ))
        else:
            await bot.send("Islem iptal edildi.")
    else:
        await bot.send(msg.content)


async def handle_telegram_message(text: str):
    """Telegram'dan gelen mesajı akıllı router'a ilet."""
    from core.conversation import route_user_message
    from integrations.gmail import load_bounced
    bot = get_bot()

    cmd = text.strip().lower()

    if cmd == "/butce":
        if bot:
            await bot.send(budget.report())
        return

    if cmd == "/durum":
        if bot:
            from integrations.vercel import get_vercel_url
            from agents.marketing import _get_demo_base, _WORKER_BASE
            demo = _get_demo_base()
            demo_src = "Vercel" if "vercel.app" in demo else ("Worker" if demo == _WORKER_BASE else "Netlify")
            bounced = len(load_bounced())
            from pathlib import Path
            sent = len(Path("memory/sent_emails.txt").read_text(encoding="utf-8").splitlines()) if Path("memory/sent_emails.txt").exists() else 0
            import json
            inbox = len(json.loads(Path("memory/inbox_emails.json").read_text(encoding="utf-8"))) if Path("memory/inbox_emails.json").exists() else 0
            b = budget.daily_usage()

            # Lead lifecycle özeti
            try:
                from core.lead_state import get_tracker
                stage_summary = get_tracker().summary()
                stage_labels = {
                    "new": "Yeni", "contacted": "Maillendi", "followed_up": "Takip1",
                    "followed_up2": "Takip2", "replied": "Yanıtladı", "bounced": "Bounce",
                    "unsubscribed": "İptal", "closed_won": "Müşteri", "closed_lost": "Kapandı",
                }
                lead_lines = "\n".join(
                    f"  • {stage_labels.get(s, s)}: {c}"
                    for s, c in sorted(stage_summary.items(), key=lambda x: x[1], reverse=True)
                ) or "  Henüz veri yok"
            except Exception:
                lead_lines = "  Veri okunamadı"

            msg = (
                f"<b>Sistem Durumu</b>\n\n"
                f"<b>LLM:</b> {b['requests']} istek, {b['tokens_used']:,} token kullanıldı\n"
                f"<b>Bütçe:</b> {'⛔ BLOKE' if b['blocked'] else '✅ Normal'} ({b['tokens_used']/20000:.1f}%)\n\n"
                f"<b>Mail:</b>\n"
                f"  • Gönderilen: {sent}\n"
                f"  • Gelen yanıt: {inbox}\n"
                f"  • Bounce (geçersiz): {bounced}\n\n"
                f"<b>Lead Aşamaları:</b>\n{lead_lines}\n\n"
                f"<b>Demo site:</b> {demo_src}\n{demo[:60]}"
            )
            await bot.send(msg)
        return

    if cmd == "/istatistik":
        if bot:
            from pathlib import Path
            import json
            sent_ids = json.loads(Path("memory/sent_message_ids.json").read_text(encoding="utf-8")) if Path("memory/sent_message_ids.json").exists() else {}
            by_sector: dict = {}
            by_lang: dict = {}
            for info in sent_ids.values():
                s = info.get("sector", "?")
                l = info.get("lang", "?")
                by_sector[s] = by_sector.get(s, 0) + 1
                by_lang[l]   = by_lang.get(l, 0) + 1
            top_sectors = sorted(by_sector.items(), key=lambda x: -x[1])[:5]
            langs_str = " | ".join(f"{l}:{n}" for l, n in sorted(by_lang.items(), key=lambda x: -x[1]))
            sector_str = "\n".join(f"  • {s}: {n}" for s, n in top_sectors)
            msg = (
                f"<b>Kampanya İstatistikleri</b>\n\n"
                f"<b>Toplam mail:</b> {len(sent_ids)}\n\n"
                f"<b>Sektörler:</b>\n{sector_str or '  Veri yok'}\n\n"
                f"<b>Diller:</b> {langs_str or 'Veri yok'}"
            )
            await bot.send(msg)
        return

    if cmd.startswith("yanit "):
        parts = text[len("yanit "):].strip().split(None, 1)
        if len(parts) < 2:
            if bot:
                await bot.send("⚠️ Kullanım: <code>yanit {reply_id} {mesaj}</code>")
            return
        reply_id, reply_text = parts[0].strip(), parts[1].strip()

        import json
        from pathlib import Path
        inbox_path = Path("memory/inbox_emails.json")
        if not inbox_path.exists():
            if bot:
                await bot.send("❌ Henüz yanıt gelen mail yok.")
            return

        inbox = json.loads(inbox_path.read_text(encoding="utf-8"))
        entry = inbox.get(reply_id)
        if not entry:
            if bot:
                await bot.send(f"❌ <code>{reply_id}</code> ID'li yanıt bulunamadı.")
            return

        from integrations.gmail import get_gmail
        gmail = get_gmail()
        if not gmail:
            if bot:
                await bot.send("❌ Gmail yapılandırılmamış.")
            return

        SIGNATURE = "\n\nSaygılar,\nKadir Sevinç - Bostok.dev\nhttps://bostok.dev"
        full_body = reply_text + SIGNATURE
        to_email = entry["from_email"]
        subject = entry.get("subject", "")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        in_reply_to = entry.get("matched_message_id", "")

        ok = await gmail.send_reply(to_email, subject, full_body, in_reply_to=in_reply_to)
        if ok:
            if bot:
                await bot.send(
                    f"✅ Yanıt gönderildi!\n"
                    f"<b>Kime:</b> {entry.get('from_name', '')} &lt;{to_email}&gt;\n"
                    f"<b>Konu:</b> {subject}"
                )
        else:
            if bot:
                await bot.send("❌ Yanıt gönderilemedi, log'ları kontrol edin.")
        return

    if cmd.startswith("revize "):
        revision_text = text[len("revize "):].strip()
        if not revision_text:
            if bot:
                await bot.send("⚠️ Kullanım: <code>revize {talimat}</code>\nÖrnek: <code>revize rengi kırmızı yap, logo büyüt</code>")
            return

        await bus.send(Message(
            sender=AgentName.SYSTEM,
            receiver=AgentName.MANAGER,
            type=MessageType.STATUS,
            content=revision_text,
            metadata={"note_type": "revizyon"},
        ))
        if bot:
            await bot.send("🔧 Revize talebi gönderildi, işleniyor...")
        return

    if cmd.startswith("/bilgi"):
        sector = text[len("/bilgi"):].strip()
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.KNOWLEDGE,
            type=MessageType.STATUS,
            content=sector or "genel",
            metadata={"cmd": "bilgi"},
        ))
        return

    if cmd.startswith("/ogret"):
        knowledge = text[len("/ogret"):].strip()
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.KNOWLEDGE,
            type=MessageType.STATUS,
            content=knowledge,
            metadata={"cmd": "ogret"},
        ))
        return

    if cmd.startswith("/pattern"):
        location = text[len("/pattern"):].strip()
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.KNOWLEDGE,
            type=MessageType.STATUS,
            content=location or "",
            metadata={"cmd": "pattern"},
        ))
        return

    if cmd == "/haftalik":
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.KNOWLEDGE,
            type=MessageType.STATUS,
            content="",
            metadata={"cmd": "haftalik"},
        ))
        return

    if cmd == "/yardim" or cmd == "/help":
        if bot:
            await bot.send(
                "<b>Bostok Agent Köyü — Komutlar</b>\n\n"
                "/durum — Sistem durumu (token, mail, demo)\n"
                "/butce — Günlük token bütçesi\n"
                "/istatistik — Kampanya istatistikleri\n"
                "/bilgi [sektör] — Sektör bilgi tabanı\n"
                "/ogret [sektör]|[bilgi] — KB'ye bilgi ekle\n"
                "/pattern [şehir] — Öğrenilen pattern'ler\n"
                "/haftalik — Haftalık öğrenme özeti\n"
                "/yardim — Bu yardım mesajı\n\n"
                "<b>📬 Müşteri Yanıt Komutları:</b>\n"
                "yanit {id} {mesaj} — Müşteriye mail yanıtı gönder\n"
                "revize {talimat} — Demo sitede değişiklik talep et\n\n"
                "Veya doğrudan mesaj yaz: <i>İstanbul'daki kafeler için kampanya başlat</i>"
            )
        return

    async def send_fn(msg: str):
        if bot:
            await bot.send(msg)

    await route_user_message(text, send_fn)


async def _wait_for_internet(timeout: int = 120):
    """İnternet bağlantısı gelene kadar bekle (max 2 dakika)."""
    import aiohttp
    for attempt in range(timeout // 5):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://api.telegram.org", timeout=aiohttp.ClientTimeout(total=4)) as r:
                    if r.status < 500:
                        if attempt > 0:
                            logger.info(f"Internet baglantisi geldi ({attempt * 5}s sonra)")
                        return
        except Exception:
            pass
        if attempt == 0:
            logger.warning("Internet baglantisi yok, bekleniyor...")
        await asyncio.sleep(5)
    logger.warning("Internet baglantisi 2 dakika icinde gelmedi, devam ediliyor")


async def main():
    setup_logging()
    logger.info("Bostok Agent Koyu baslatiliyor...")
    await _wait_for_internet()
    logger.info(budget.report())

    # Demo site deploy — Vercel (öncelikli) → Netlify → Worker fallback
    from integrations.vercel import deploy_demo_site as vercel_deploy
    vercel_url = await vercel_deploy("demo_site")
    if vercel_url:
        logger.info(f"Demo site (Vercel): {vercel_url}")
    else:
        netlify = init_netlify()
        if netlify:
            netlify_url = await netlify.deploy_demo_site("demo_site")
            if netlify_url:
                logger.info(f"Demo site (Netlify): {netlify_url}")
            else:
                logger.info("Demo site: Cloudflare Worker kullaniliyor")

    # Gmail başlat
    gmail = init_gmail()
    if gmail:
        logger.info(f"Gmail hazir: {gmail.stats}")
        init_reader(gmail._user, gmail._password)
        logger.info("Gmail inbox takibi aktif")
    else:
        logger.warning("Gmail bagli degil - sadece sablon modu")

    # Telegram botu başlat
    bot = init_bot()
    if bot:
        logger.info("Telegram bagli - mesaj atabilirsiniz!")
    else:
        logger.warning("Telegram bagli degil - sadece konsol modu")

    # Bildirim listener
    bus.add_listener(notify_handler)

    # Tüm agent'ları başlat
    agents = [
        ManagerAgent(), AnalystAgent(), MarketingAgent(),
        QuoteAgent(), ContentAgent(), DesignerAgent(),
        DeveloperAgent(), QAAgent(), DeployAgent(),
        InboxWatcherAgent(), FollowupAgent(), KnowledgeAgent(),
    ]
    logger.info(f"{len(agents)} agent baslatildi")

    tasks = [asyncio.create_task(a.run()) for a in agents]
    tasks.append(asyncio.create_task(budget_monitor()))
    tasks.append(asyncio.create_task(marketing_scheduler()))

    # Telegram polling başlat
    if bot:
        tasks.append(asyncio.create_task(
            bot.poll_updates(on_message=handle_telegram_message)
        ))

    # Komut satırı argümanı varsa demo görevi çalıştır
    if len(sys.argv) > 1:
        demo_task = " ".join(sys.argv[1:])
        await asyncio.sleep(1)
        logger.info(f"Demo gorevi: {demo_task}")
        await bus.send(Message(
            sender=AgentName.SYSTEM, receiver=AgentName.MANAGER,
            type=MessageType.CLIENT_REQUEST, content=demo_task,
        ))
        if bot:
            await bot.send(f"Gorev baslatildi: {demo_task[:100]}")

    if bot:
        await bot.send(
            "Bostok Agent Koyu aktif!\n\n"
            "Musteri talebi gondermek icin direkt yazin.\n"
            "Komutlar icin /yardim yazin."
        )
        logger.info("Hazir! Telegram'dan mesaj atabilirsiniz.")
    else:
        logger.info("Demo icin: python main.py 'musteri talebi buraya'")

    async def _embed_loop():
        """Her 10 dakikada yeni memory'lere embedding üret."""
        while True:
            try:
                await asyncio.sleep(600)
                from core.memory import store
                await store.embed_pending(limit=30)
            except Exception:
                pass

    tasks.append(_embed_loop())

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Sistem kapatiliyor...")
        for a in agents:
            a.stop()


if __name__ == "__main__":
    asyncio.run(main())
