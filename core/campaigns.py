"""Kampanya listesi — tüm sektör/lokasyon kombinasyonları."""

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

    # ── Türkiye — Tarım & Hayvancılık ────────────────────────────
    {"sector": "tarim makineleri",      "locations": ["Konya", "Ankara", "Bursa", "Adana", "Samsun", "Sakarya", "Corum", "Tekirdag"], "langs": ["tr"]},
    {"sector": "hayvancılık",           "locations": ["Konya", "Erzurum", "Samsun", "Trabzon", "Sivas", "Ordu", "Rize", "Kars", "Diyarbakir"], "langs": ["tr"]},
    {"sector": "su urunleri",           "locations": ["Trabzon", "Rize", "Ordu", "Samsun", "Mersin", "Antalya", "Izmir", "Mugla"], "langs": ["tr"]},
    {"sector": "seracılık",             "locations": ["Antalya", "Mersin", "Adana", "Izmir", "Mugla", "Hatay"], "langs": ["tr"]},

    # ── Türkiye — Gıda & İçecek Üretimi ──────────────────────────
    {"sector": "gida uretimi",          "locations": ["Istanbul", "Bursa", "Konya", "Ankara", "Izmir", "Adana", "Gaziantep", "Tekirdag", "Sakarya", "Kayseri"], "langs": ["tr"]},
    {"sector": "icecek uretimi",        "locations": ["Istanbul", "Bursa", "Ankara", "Izmir", "Adana", "Tekirdag", "Sakarya"], "langs": ["tr"]},

    # ── Türkiye — Mobilya & Ahşap ─────────────────────────────────
    {"sector": "mobilya uretimi",       "locations": ["Istanbul", "Bursa", "Kayseri", "Ankara", "Izmir", "Konya", "Tekirdag", "Sakarya"], "langs": ["tr"]},
    {"sector": "ahsap isleme",          "locations": ["Bursa", "Istanbul", "Kayseri", "Trabzon", "Rize", "Artvin", "Sakarya", "Duzce"], "langs": ["tr"]},

    # ── Türkiye — Ambalaj & Plastik & Kimya ──────────────────────
    {"sector": "ambalaj sanayi",        "locations": ["Istanbul", "Bursa", "Kocaeli", "Izmir", "Tekirdag", "Sakarya", "Ankara", "Gaziantep"], "langs": ["tr"]},
    {"sector": "plastik uretimi",       "locations": ["Istanbul", "Bursa", "Kocaeli", "Izmir", "Gaziantep", "Tekirdag", "Sakarya", "Ankara"], "langs": ["tr"]},
    {"sector": "kozmetik uretimi",      "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Tekirdag", "Kocaeli"], "langs": ["tr"]},
    {"sector": "matbaa",                "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Kayseri", "Samsun", "Tekirdag"], "langs": ["tr"]},

    # ── Türkiye — Metal & Makine & Seramik ───────────────────────
    {"sector": "metal isleme",          "locations": ["Istanbul", "Bursa", "Kocaeli", "Ankara", "Izmir", "Konya", "Gaziantep", "Tekirdag", "Sakarya", "Kahramanmaras"], "langs": ["tr"]},
    {"sector": "aluminyum uretimi",     "locations": ["Istanbul", "Bursa", "Kocaeli", "Izmir", "Tekirdag", "Sakarya", "Ankara"], "langs": ["tr"]},
    {"sector": "seramik uretimi",       "locations": ["Istanbul", "Izmir", "Kutahya", "Bilecik", "Bursa", "Canakkale", "Eskisehir"], "langs": ["tr"]},
    {"sector": "makine uretimi",        "locations": ["Istanbul", "Bursa", "Ankara", "Izmir", "Konya", "Kocaeli", "Gaziantep", "Sakarya", "Eskisehir"], "langs": ["tr"]},
    {"sector": "mucevher",              "locations": ["Istanbul", "Ankara", "Izmir", "Trabzon", "Rize", "Kayseri"], "langs": ["tr"]},

    # ── Türkiye — Enerji & Çevre ──────────────────────────────────
    {"sector": "gunes enerjisi",        "locations": ["Istanbul", "Ankara", "Izmir", "Antalya", "Konya", "Adana", "Bursa", "Gaziantep", "Diyarbakir", "Sanliurfa", "Kayseri"], "langs": ["tr"]},
    {"sector": "geri donusum",          "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Kocaeli", "Tekirdag", "Sakarya", "Samsun"], "langs": ["tr"]},
    {"sector": "atik yonetimi",         "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Kocaeli", "Samsun", "Antalya"], "langs": ["tr"]},

    # ── Türkiye — Lojistik & Kargo ────────────────────────────────
    {"sector": "kargo hizmetleri",      "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Kayseri", "Tekirdag", "Sakarya"], "langs": ["tr"]},
    {"sector": "kurye hizmetleri",      "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Kayseri", "Antalya"], "langs": ["tr"]},

    # ── Türkiye — Danışmanlık & İK ────────────────────────────────
    {"sector": "danismanlik",           "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Kayseri", "Antalya", "Tekirdag"], "langs": ["tr"]},
    {"sector": "insan kaynaklari",      "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Kocaeli", "Adana", "Antalya"], "langs": ["tr"]},

    # ── Türkiye — Sağlık (Ek) ─────────────────────────────────────
    {"sector": "laboraturvar",          "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Kayseri", "Samsun", "Antalya"], "langs": ["tr"]},
    {"sector": "saglik turizmi",        "locations": ["Istanbul", "Ankara", "Izmir", "Antalya", "Bursa", "Adana"], "langs": ["tr", "en"]},
    {"sector": "yasli bakım evi",       "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Antalya", "Kayseri", "Samsun"], "langs": ["tr"]},
    {"sector": "medikal cihaz",         "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Kocaeli", "Antalya"], "langs": ["tr"]},

    # ── Türkiye — Turizm & Etkinlik ───────────────────────────────
    {"sector": "tur operatoru",         "locations": ["Istanbul", "Antalya", "Izmir", "Cappadocia", "Bodrum", "Trabzon", "Erzurum", "Mugla"], "langs": ["tr", "en"]},
    {"sector": "etkinlik organizasyon", "locations": ["Istanbul", "Ankara", "Izmir", "Antalya", "Bursa", "Adana", "Samsun"], "langs": ["tr"]},

    # ── Türkiye — Güvenlik & Tesis ────────────────────────────────
    {"sector": "guvenlik sirketi",      "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Kayseri", "Tekirdag", "Sakarya", "Diyarbakir", "Antalya"], "langs": ["tr"]},
    {"sector": "tesis yonetimi",        "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Kocaeli", "Adana", "Mersin", "Antalya"], "langs": ["tr"]},

    # ── Türkiye — Reklam & Yazılım ────────────────────────────────
    {"sector": "reklam ajansi",         "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Antalya", "Kayseri"], "langs": ["tr"]},
    {"sector": "yazilim gelistirme",    "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Kocaeli", "Eskisehir", "Samsun", "Antalya"], "langs": ["tr"]},

    # ── Türkiye — Teknik & Ev Hizmetleri ──────────────────────────
    {"sector": "teknik servis",         "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Samsun", "Kayseri", "Tekirdag", "Sakarya", "Antalya"], "langs": ["tr"]},
    {"sector": "ev hizmetleri",         "locations": ["Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Antalya", "Kayseri"], "langs": ["tr"]},

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
    {"sector": "mobelwerk",        "locations": ["Stuttgart", "Munich", "Frankfurt", "Cologne", "Nuremberg", "Leipzig", "Hannover"], "langs": ["de"]},
    {"sector": "metallverarbeitung","locations": ["Stuttgart", "Munich", "Frankfurt", "Dusseldorf", "Nuremberg", "Hannover", "Dortmund", "Cologne"], "langs": ["de"]},
    {"sector": "druckerei",        "locations": ["Berlin", "Hamburg", "Munich", "Frankfurt", "Stuttgart", "Nuremberg", "Leipzig", "Cologne"], "langs": ["de"]},
    {"sector": "kosmetikstudio",   "locations": ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Stuttgart", "Dusseldorf"], "langs": ["de"]},
    {"sector": "pflegedienst",     "locations": ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Stuttgart", "Nuremberg", "Hannover"], "langs": ["de"]},
    {"sector": "logistik",         "locations": ["Hamburg", "Cologne", "Frankfurt", "Stuttgart", "Munich", "Dortmund", "Hannover", "Bremen"], "langs": ["de"]},
    {"sector": "sicherheitsdienst","locations": ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Dortmund"], "langs": ["de"]},
    {"sector": "solarenergie",     "locations": ["Munich", "Stuttgart", "Frankfurt", "Cologne", "Nuremberg", "Hamburg", "Berlin"], "langs": ["de"]},
    {"sector": "veranstaltungsservice", "locations": ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Stuttgart"], "langs": ["de"]},

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
    {"sector": "courier service",  "locations": ["London", "Manchester", "Birmingham", "Leeds", "Liverpool", "Bristol", "Sheffield"], "langs": ["en"]},
    {"sector": "security company", "locations": ["London", "Manchester", "Birmingham", "Leeds", "Liverpool", "Bristol"], "langs": ["en"]},
    {"sector": "care home",        "locations": ["London", "Manchester", "Birmingham", "Leeds", "Liverpool", "Sheffield", "Bristol", "Newcastle"], "langs": ["en"]},
    {"sector": "printing company", "locations": ["London", "Manchester", "Birmingham", "Leeds", "Liverpool", "Bristol"], "langs": ["en"]},
    {"sector": "marketing agency", "locations": ["London", "Manchester", "Birmingham", "Leeds", "Bristol", "Edinburgh"], "langs": ["en"]},
    {"sector": "tour operator",    "locations": ["London", "Manchester", "Edinburgh", "Bristol", "Liverpool"], "langs": ["en"]},
    {"sector": "solar energy",     "locations": ["London", "Manchester", "Birmingham", "Leeds", "Bristol", "Cardiff", "Edinburgh"], "langs": ["en"]},
    {"sector": "event planning",   "locations": ["London", "Manchester", "Birmingham", "Leeds", "Liverpool", "Bristol"], "langs": ["en"]},
    {"sector": "catering company", "locations": ["London", "Manchester", "Birmingham", "Leeds", "Liverpool", "Bristol"], "langs": ["en"]},

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
    {"sector": "solar energy",     "locations": ["Los Angeles", "Phoenix", "Dallas", "Miami", "Atlanta", "Denver", "Las Vegas", "Austin", "San Diego"], "langs": ["en"]},
    {"sector": "marketing agency", "locations": ["New York", "Los Angeles", "Chicago", "Miami", "Atlanta", "Dallas", "Austin", "Seattle"],              "langs": ["en"]},
    {"sector": "event planning",   "locations": ["New York", "Los Angeles", "Chicago", "Miami", "Las Vegas", "Atlanta", "Dallas", "Houston"],           "langs": ["en"]},
    {"sector": "tour operator",    "locations": ["New York", "Los Angeles", "Miami", "Las Vegas", "Orlando", "San Francisco", "Nashville"],             "langs": ["en"]},
    {"sector": "catering company", "locations": ["New York", "Los Angeles", "Chicago", "Miami", "Houston", "Dallas", "Atlanta"],                        "langs": ["en"]},
    {"sector": "courier service",  "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Dallas", "Miami", "Atlanta"],                        "langs": ["en"]},
    {"sector": "security company", "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Dallas", "Miami", "Atlanta"],                        "langs": ["en"]},
    {"sector": "care home",        "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Miami", "Atlanta", "Phoenix"],                       "langs": ["en"]},
    {"sector": "printing company", "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Dallas", "Atlanta"],                                 "langs": ["en"]},

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

    # ── Türkiye — Eksik İller ──────────────────────────────────────
    {"sector": "restoran",       "locations": ["Balikesir", "Manisa", "Aydin", "Kutahya", "Afyon", "Usak", "Isparta", "Burdur", "Bilecik", "Yalova", "Karaman", "Nevsehir", "Aksaray", "Yozgat", "Kirikkale", "Karabuk", "Zonguldak", "Bartin", "Kastamonu", "Sinop", "Bolu", "Giresun", "Gumushane", "Bayburt", "Erzincan", "Tunceli", "Bingol", "Mus", "Bitlis", "Siirt", "Batman", "Sirnak", "Agri", "Kars", "Ardahan", "Igdir", "Hakkari"], "langs": ["tr"]},
    {"sector": "kafe",           "locations": ["Balikesir", "Manisa", "Aydin", "Kutahya", "Afyon", "Isparta", "Karaman", "Nevsehir", "Karabuk", "Zonguldak", "Kastamonu", "Bolu", "Giresun"], "langs": ["tr"]},
    {"sector": "dis hekimi",     "locations": ["Balikesir", "Manisa", "Aydin", "Kutahya", "Afyon", "Usak", "Isparta", "Burdur", "Bilecik", "Yalova", "Karabuk", "Zonguldak", "Kastamonu", "Bolu", "Giresun"], "langs": ["tr"]},
    {"sector": "avukat",         "locations": ["Balikesir", "Manisa", "Aydin", "Isparta", "Yalova", "Karabuk", "Zonguldak", "Bolu", "Giresun"], "langs": ["tr"]},
    {"sector": "guzellik salonu","locations": ["Balikesir", "Manisa", "Aydin", "Kutahya", "Afyon", "Isparta", "Yalova", "Zonguldak", "Bolu", "Giresun"], "langs": ["tr"]},
    {"sector": "oto servis",     "locations": ["Balikesir", "Manisa", "Kutahya", "Afyon", "Bilecik", "Karaman", "Karabuk", "Zonguldak", "Bolu", "Giresun"], "langs": ["tr"]},

    # ── ABD ─────────────────────────────────────────────────────
    {"sector": "restaurant",     "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville", "Fort Worth", "Columbus", "Charlotte", "Indianapolis", "San Francisco", "Seattle", "Denver", "Nashville", "Las Vegas", "Louisville", "Memphis", "Portland", "Baltimore", "Milwaukee", "Albuquerque", "Fresno", "Atlanta", "Miami", "Boston"], "langs": ["en"]},
    {"sector": "dental clinic",  "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Dallas", "San Francisco", "Seattle", "Denver", "Atlanta", "Miami", "Boston", "Las Vegas", "Nashville", "Portland"], "langs": ["en"]},
    {"sector": "beauty salon",   "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Miami", "Atlanta", "Dallas", "Phoenix", "San Francisco", "Seattle", "Denver", "Boston", "Las Vegas"], "langs": ["en"]},
    {"sector": "gym",            "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Miami", "Dallas", "San Francisco", "Seattle", "Denver", "Atlanta", "Phoenix", "Boston"], "langs": ["en"]},
    {"sector": "law firm",       "locations": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Dallas", "Miami", "Atlanta", "San Francisco", "Boston", "Seattle", "Denver"], "langs": ["en"]},
    {"sector": "real estate",    "locations": ["New York", "Los Angeles", "Miami", "Chicago", "Dallas", "Houston", "San Francisco", "Las Vegas", "Phoenix", "Atlanta", "Seattle", "Denver"], "langs": ["en"]},
    {"sector": "accounting firm","locations": ["New York", "Los Angeles", "Chicago", "Houston", "Miami", "Dallas", "Atlanta", "Phoenix", "San Francisco", "Seattle"], "langs": ["en"]},

    # ── İngiltere ─────────────────────────────────────────────────
    {"sector": "restaurant",     "locations": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool", "Sheffield", "Bristol", "Newcastle", "Nottingham", "Leicester", "Edinburgh", "Cardiff", "Oxford", "Cambridge", "Brighton", "Portsmouth", "Southampton", "Reading", "Coventry", "Belfast"], "langs": ["en"]},
    {"sector": "dental clinic",  "locations": ["London", "Manchester", "Birmingham", "Leeds", "Liverpool", "Bristol", "Newcastle", "Edinburgh", "Cardiff", "Leicester", "Nottingham"], "langs": ["en"]},
    {"sector": "beauty salon",   "locations": ["London", "Manchester", "Birmingham", "Leeds", "Liverpool", "Bristol", "Newcastle", "Edinburgh", "Cardiff"], "langs": ["en"]},
    {"sector": "accounting firm","locations": ["London", "Manchester", "Birmingham", "Leeds", "Liverpool", "Bristol", "Edinburgh"], "langs": ["en"]},

    # ── Kanada ────────────────────────────────────────────────────
    {"sector": "restaurant",     "locations": ["Toronto", "Vancouver", "Montreal", "Calgary", "Edmonton", "Ottawa", "Winnipeg", "Quebec City", "Hamilton", "Kitchener", "London Ontario", "Halifax", "Victoria", "Saskatoon", "Regina"], "langs": ["en"]},
    {"sector": "dental clinic",  "locations": ["Toronto", "Vancouver", "Calgary", "Edmonton", "Ottawa", "Montreal", "Winnipeg", "Halifax"], "langs": ["en"]},
    {"sector": "beauty salon",   "locations": ["Toronto", "Vancouver", "Calgary", "Edmonton", "Ottawa", "Montreal"], "langs": ["en"]},

    # ── Avustralya ────────────────────────────────────────────────
    {"sector": "restaurant",     "locations": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast", "Newcastle", "Canberra", "Wollongong", "Hobart", "Geelong", "Townsville", "Cairns", "Darwin"], "langs": ["en"]},
    {"sector": "dental clinic",  "locations": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast", "Canberra", "Hobart"], "langs": ["en"]},
    {"sector": "beauty salon",   "locations": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast"], "langs": ["en"]},

    # ── İrlanda / Yeni Zelanda ────────────────────────────────────
    {"sector": "restaurant",     "locations": ["Dublin", "Cork", "Limerick", "Galway", "Waterford"], "langs": ["en"]},
    {"sector": "restaurant",     "locations": ["Auckland", "Wellington", "Christchurch", "Hamilton", "Tauranga", "Dunedin"], "langs": ["en"]},

    # ── Portekiz ──────────────────────────────────────────────────
    {"sector": "restaurante",    "locations": ["Lisbon", "Porto", "Braga", "Coimbra", "Faro", "Setubal", "Funchal"], "langs": ["pt"]},
    {"sector": "clinica dentaria","locations": ["Lisbon", "Porto", "Braga", "Coimbra", "Faro"], "langs": ["pt"]},
    {"sector": "salao de beleza","locations": ["Lisbon", "Porto", "Braga", "Coimbra"], "langs": ["pt"]},

    # ── İspanya ───────────────────────────────────────────────────
    {"sector": "restaurante",    "locations": ["Madrid", "Barcelona", "Valencia", "Seville", "Zaragoza", "Malaga", "Murcia", "Palma", "Las Palmas", "Bilbao", "Alicante", "Cordoba", "Valladolid", "Vigo", "Granada", "Alicante", "Santander", "Pamplona", "San Sebastian", "Salamanca"], "langs": ["es"]},
    {"sector": "clinica dental", "locations": ["Madrid", "Barcelona", "Valencia", "Seville", "Malaga", "Bilbao", "Alicante", "Murcia", "Zaragoza", "Palma"], "langs": ["es"]},
    {"sector": "salon de belleza","locations": ["Madrid", "Barcelona", "Valencia", "Seville", "Malaga", "Bilbao", "Zaragoza"], "langs": ["es"]},
    {"sector": "gimnasio",       "locations": ["Madrid", "Barcelona", "Valencia", "Seville", "Bilbao", "Malaga"], "langs": ["es"]},

    # ── İtalya ────────────────────────────────────────────────────
    {"sector": "ristorante",     "locations": ["Rome", "Milan", "Naples", "Turin", "Palermo", "Genoa", "Bologna", "Florence", "Bari", "Venice", "Messina", "Verona", "Padua", "Trieste", "Catania", "Brescia", "Reggio Calabria", "Modena", "Livorno", "Cagliari"], "langs": ["it"]},
    {"sector": "studio dentistico","locations": ["Rome", "Milan", "Naples", "Turin", "Florence", "Bologna", "Venice", "Genoa", "Bari", "Palermo"], "langs": ["it"]},
    {"sector": "parrucchiere",   "locations": ["Rome", "Milan", "Naples", "Turin", "Florence", "Bologna", "Venice"], "langs": ["it"]},

    # ── Brezilya ──────────────────────────────────────────────────
    {"sector": "restaurante",    "locations": ["Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Brasilia", "Salvador", "Fortaleza", "Manaus", "Curitiba", "Recife", "Porto Alegre", "Belem", "Goiania", "Campinas", "Sao Luis", "Natal", "Teresina", "Campo Grande", "Maceio", "Joao Pessoa", "Florianopolis"], "langs": ["pt"]},
    {"sector": "clinica odontologica","locations": ["Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Brasilia", "Salvador", "Curitiba", "Porto Alegre", "Fortaleza", "Recife"], "langs": ["pt"]},
    {"sector": "salao de beleza","locations": ["Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Brasilia", "Curitiba", "Porto Alegre", "Salvador"], "langs": ["pt"]},
    {"sector": "academia",       "locations": ["Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Brasilia", "Curitiba", "Porto Alegre"], "langs": ["pt"]},

    # ── Meksika ───────────────────────────────────────────────────
    {"sector": "restaurante",    "locations": ["Mexico City", "Guadalajara", "Monterrey", "Puebla", "Tijuana", "Leon", "Juarez", "Torreon", "Queretaro", "Merida", "San Luis Potosi", "Aguascalientes", "Culiacan", "Hermosillo", "Cancun", "Mexicali", "Acapulco", "Morelia", "Veracruz"], "langs": ["es"]},
    {"sector": "clinica dental", "locations": ["Mexico City", "Guadalajara", "Monterrey", "Puebla", "Tijuana", "Queretaro", "Merida", "Cancun"], "langs": ["es"]},
    {"sector": "salon de belleza","locations": ["Mexico City", "Guadalajara", "Monterrey", "Puebla", "Tijuana", "Queretaro", "Merida"], "langs": ["es"]},

    # ── Kolombiya / Arjantin / Şili / Peru ────────────────────────
    {"sector": "restaurante",    "locations": ["Bogota", "Medellin", "Cali", "Barranquilla", "Cartagena", "Bucaramanga", "Pereira", "Santa Marta", "Manizales", "Ibague"], "langs": ["es"]},
    {"sector": "restaurante",    "locations": ["Buenos Aires", "Cordoba", "Rosario", "Mendoza", "La Plata", "Tucuman", "Mar del Plata", "Salta", "Santa Fe", "San Juan"], "langs": ["es"]},
    {"sector": "restaurante",    "locations": ["Santiago", "Valparaiso", "Concepcion", "La Serena", "Antofagasta", "Temuco", "Rancagua", "Talca", "Arica"], "langs": ["es"]},
    {"sector": "restaurante",    "locations": ["Lima", "Arequipa", "Trujillo", "Chiclayo", "Piura", "Iquitos", "Cusco"], "langs": ["es"]},

    # ── Güneydoğu Asya ────────────────────────────────────────────
    {"sector": "restaurant",     "locations": ["Bangkok", "Chiang Mai", "Phuket", "Pattaya", "Hua Hin", "Krabi", "Koh Samui"], "langs": ["en"]},
    {"sector": "dental clinic",  "locations": ["Bangkok", "Chiang Mai", "Phuket"], "langs": ["en"]},
    {"sector": "restaurant",     "locations": ["Kuala Lumpur", "George Town", "Johor Bahru", "Ipoh", "Shah Alam", "Petaling Jaya", "Kota Kinabalu", "Kuching"], "langs": ["en"]},
    {"sector": "restaurant",     "locations": ["Singapore"], "langs": ["en"]},
    {"sector": "restaurant",     "locations": ["Manila", "Cebu City", "Davao", "Quezon City", "Makati", "Pasig", "Taguig", "Antipolo", "Cagayan de Oro", "Zamboanga"], "langs": ["en"]},
    {"sector": "dental clinic",  "locations": ["Manila", "Cebu City", "Makati"], "langs": ["en"]},
    {"sector": "restaurant",     "locations": ["Jakarta", "Surabaya", "Bandung", "Medan", "Bekasi", "Denpasar", "Makassar", "Semarang", "Palembang", "Tangerang"], "langs": ["en"]},
    {"sector": "restaurant",     "locations": ["Ho Chi Minh City", "Hanoi", "Da Nang", "Hoi An", "Nha Trang", "Hue", "Can Tho"], "langs": ["en"]},
    {"sector": "dental clinic",  "locations": ["Ho Chi Minh City", "Hanoi", "Da Nang"], "langs": ["en"]},

    # ── Hindistan ─────────────────────────────────────────────────
    {"sector": "restaurant",     "locations": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Surat", "Lucknow", "Kanpur", "Nagpur", "Indore", "Bhopal", "Patna", "Vadodara", "Goa", "Kochi", "Coimbatore", "Agra", "Visakhapatnam", "Ludhiana", "Madurai", "Nashik", "Faridabad", "Meerut", "Rajkot", "Varanasi", "Srinagar"], "langs": ["en"]},
    {"sector": "dental clinic",  "locations": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Pune", "Ahmedabad", "Kochi", "Kolkata", "Jaipur"], "langs": ["en"]},
    {"sector": "beauty salon",   "locations": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Pune", "Ahmedabad", "Kolkata", "Jaipur"], "langs": ["en"]},
    {"sector": "gym",            "locations": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Pune", "Ahmedabad"], "langs": ["en"]},

    # ── Orta Doğu — Genişletilmiş ─────────────────────────────────
    {"sector": "restaurant",     "locations": ["Kuwait City", "Doha", "Manama", "Muscat", "Amman", "Beirut", "Baghdad", "Cairo", "Alexandria", "Riyadh", "Jeddah", "Dammam", "Mecca", "Medina", "Khobar", "Tabuk", "Yanbu", "Abha", "Najran"], "langs": ["en"]},
    {"sector": "dental clinic",  "locations": ["Dubai", "Abu Dhabi", "Kuwait City", "Doha", "Muscat", "Amman", "Riyadh", "Jeddah", "Sharjah", "Ajman"], "langs": ["en"]},
    {"sector": "beauty salon",   "locations": ["Dubai", "Abu Dhabi", "Kuwait City", "Doha", "Muscat", "Riyadh", "Jeddah"], "langs": ["en"]},

    # ── Afrika ────────────────────────────────────────────────────
    {"sector": "restaurant",     "locations": ["Lagos", "Abuja", "Ibadan", "Kano", "Port Harcourt", "Nairobi", "Mombasa", "Dar es Salaam", "Accra", "Cape Town", "Johannesburg", "Durban", "Pretoria", "Casablanca", "Marrakech", "Tunis", "Algiers", "Addis Ababa", "Kampala", "Kigali", "Dakar", "Abidjan", "Douala"], "langs": ["en"]},
    {"sector": "dental clinic",  "locations": ["Lagos", "Nairobi", "Cape Town", "Johannesburg", "Accra", "Casablanca", "Abuja", "Dar es Salaam"], "langs": ["en"]},

    # ── İskandinav ────────────────────────────────────────────────
    {"sector": "restaurant",     "locations": ["Stockholm", "Gothenburg", "Malmo", "Uppsala", "Vasteras", "Orebro", "Oslo", "Bergen", "Stavanger", "Trondheim", "Drammen", "Copenhagen", "Aarhus", "Odense", "Aalborg", "Helsinki", "Tampere", "Turku", "Oulu"], "langs": ["en"]},
    {"sector": "dental clinic",  "locations": ["Stockholm", "Gothenburg", "Oslo", "Bergen", "Copenhagen", "Helsinki", "Tampere"], "langs": ["en"]},

    # ── Doğu Avrupa ───────────────────────────────────────────────
    {"sector": "restaurant",     "locations": ["Prague", "Brno", "Ostrava", "Pilsen", "Bucharest", "Cluj-Napoca", "Timisoara", "Iasi", "Budapest", "Debrecen", "Miskolc", "Pecs", "Sofia", "Plovdiv", "Varna", "Burgas", "Belgrade", "Novi Sad", "Zagreb", "Split", "Dubrovnik", "Rijeka", "Sarajevo", "Ljubljana", "Maribor", "Bratislava", "Kosice", "Warsaw", "Krakow", "Gdansk", "Wroclaw", "Poznan", "Lodz", "Vilnius", "Riga", "Tallinn"], "langs": ["en"]},
    {"sector": "dental clinic",  "locations": ["Prague", "Bucharest", "Budapest", "Warsaw", "Belgrade", "Sofia", "Zagreb", "Bratislava", "Vilnius", "Riga", "Tallinn"], "langs": ["en"]},

    # ── Japonya / Güney Kore / Çin ────────────────────────────────
    {"sector": "restaurant",     "locations": ["Tokyo", "Osaka", "Yokohama", "Nagoya", "Sapporo", "Fukuoka", "Kobe", "Kyoto", "Kawasaki", "Saitama", "Hiroshima", "Sendai", "Kitakyushu", "Chiba"], "langs": ["en"]},
    {"sector": "restaurant",     "locations": ["Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju", "Suwon", "Ulsan", "Changwon", "Goyang"], "langs": ["en"]},
    {"sector": "restaurant",     "locations": ["Shanghai", "Beijing", "Shenzhen", "Guangzhou", "Chengdu", "Hangzhou", "Wuhan", "Chongqing", "Hong Kong", "Macau", "Nanjing", "Tianjin", "Xi'an", "Suzhou"], "langs": ["en"]},
]
