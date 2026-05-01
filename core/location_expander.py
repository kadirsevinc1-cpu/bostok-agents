"""
TR provinces → districts lookup.
Returns province + key districts for Maps API searches.
"""

MAX_DISTRICTS = 6

_TR_DISTRICTS: dict[str, list[str]] = {
    "tekirdag":      ["Corlu", "Cerkezkoy", "Kapakli", "Malkara", "Muratli", "Sarkoy", "Hayrabolu", "Saray", "Ergene", "Marmaraereglisi"],
    "edirne":        ["Uzunkopru", "Kesan", "Ipsala", "Havsa", "Enez"],
    "kirklareli":    ["Luleburgaz", "Babaeski", "Vize", "Pinarhisar"],
    "canakkale":     ["Biga", "Can", "Ezine", "Gelibolu", "Lapseki"],
    "balikesir":     ["Bandirma", "Edremit", "Burhaniye", "Bigadic", "Susurluk"],
    "manisa":        ["Turgutlu", "Akhisar", "Salihli", "Soma", "Alasehir"],
    "aydin":         ["Nazilli", "Kusadasi", "Soke", "Didim", "Incirliova"],
    "denizli":       ["Acipayam", "Saraykoy", "Tavas", "Buldan", "Cardak"],
    "mugla":         ["Marmaris", "Fethiye", "Milas", "Datca", "Koycegiz", "Ortaca"],
    "isparta":       ["Egirdir", "Senirkent", "Yalvac", "Sarkikaraagac"],
    "burdur":        ["Bucak", "Golhisar", "Tefenni"],
    "antalya":       ["Konyaalti", "Kepez", "Muratpasa", "Manavgat", "Serik", "Kemer"],
    "mersin":        ["Tarsus", "Silifke", "Erdemli", "Anamur", "Mezitli"],
    "adana":         ["Kozan", "Ceyhan", "Karaisali", "Saricam"],
    "hatay":         ["Iskenderun", "Dortyol", "Reyhanli", "Samandagi", "Erzin"],
    "kahramanmaras": ["Elbistan", "Afsin", "Pazarcik", "Turkoglu"],
    "sanliurfa":     ["Siverek", "Birecik", "Viransehir", "Halfeti"],
    "gaziantep":     ["Nizip", "Islahiye", "Nurdagi", "Oguzeli"],
    "diyarbakir":    ["Ergani", "Silvan", "Bismil", "Cinar"],
    "mardin":        ["Kiziltepe", "Nusaybin", "Midyat", "Derik"],
    "sivas":         ["Sarkisla", "Susehri", "Gemerek", "Kangal"],
    "tokat":         ["Turhal", "Niksar", "Erbaa", "Zile"],
    "amasya":        ["Merzifon", "Suluova", "Tasova"],
    "corum":         ["Sungurlu", "Osmancik", "Iskilip", "Alaca"],
    "kayseri":       ["Develi", "Bunyan", "Pinarbasi"],
    "nevsehir":      ["Urgup", "Avanos", "Hacibektas"],
    "aksaray":       ["Guzelyurt", "Ortakoy"],
    "konya":         ["Eregli", "Seydisehir", "Aksehir", "Beysehir", "Ilgin"],
    "eskisehir":     ["Sivrihisar", "Cifteler", "Mahmudiye"],
    "kutahya":       ["Gediz", "Simav", "Tavsanli"],
    "afyon":         ["Sandikli", "Bolvadin", "Dinar", "Emirdag"],
    "usak":          ["Esme", "Sivasli", "Banaz"],
    "bilecik":       ["Bozuyuk", "Osmaneli", "Sogut"],
    "yalova":        ["Cinarcik", "Altinova", "Armutlu"],
    "kocaeli":       ["Gebze", "Golcuk", "Darica", "Cayirova"],
    "sakarya":       ["Karasu", "Akyazi", "Hendek", "Pamukova"],
    "bolu":          ["Goynuk", "Mengen", "Mudurnu"],
    "duzce":         ["Akcakoca", "Golyaka", "Gumusova"],
    "zonguldak":     ["Caycuma", "Eregli", "Alapli"],
    "bartin":        ["Amasra", "Kurucasile"],
    "karabuk":       ["Safranbolu", "Eskipazar"],
    "kastamonu":     ["Tosya", "Taskopru", "Inebolu"],
    "sinop":         ["Boyabat", "Gerze"],
    "samsun":        ["Bafra", "Terme", "Havza", "Vezirkopru"],
    "ordu":          ["Unye", "Fatsa", "Persembe"],
    "giresun":       ["Espiye", "Bulancak", "Gorele"],
    "trabzon":       ["Akcaabat", "Of", "Yomra", "Surmene"],
    "rize":          ["Ardesen", "Findikli", "Pazar"],
    "artvin":        ["Arhavi", "Hopa", "Borcka"],
    "erzurum":       ["Pasinler", "Horasan", "Aziziye"],
    "erzincan":      ["Refahiye", "Uzumlu", "Kemah"],
    "gumushane":     ["Kelkit", "Kurtun"],
    "malatya":       ["Battalgazi", "Yesilyurt", "Akcadag", "Darende"],
    "elazig":        ["Keban", "Sivrice"],
    "tunceli":       ["Pertek"],
    "bingol":        ["Genc", "Karliova"],
    "mus":           ["Malazgirt", "Varto"],
    "bitlis":        ["Tatvan", "Ahlat"],
    "van":           ["Ercis", "Baskale"],
    "hakkari":       ["Yuksekova"],
    "siirt":         ["Kurtalan", "Baykan"],
    "batman":        ["Kozluk", "Besiri"],
    "sirnak":        ["Cizre", "Silopi"],
    "agri":          ["Dogubayazit", "Patnos"],
    "kars":          ["Sarikamis", "Kagizman"],
    "igdir":         ["Aralik"],
    "ardahan":       ["Posof"],
    "bayburt":       ["Aydintepe"],
    "izmir":         ["Bornova", "Buca", "Karsiyaka", "Bayrakli", "Gaziemir"],
    "bursa":         ["Inegol", "Gemlik", "Karacabey", "Orhangazi", "Mudanya"],
    "istanbul":      [],
    "ankara":        [],
}


def expand_location(location: str) -> list[str]:
    """Returns [location] + key districts for TR provinces, or [location] only."""
    districts = _TR_DISTRICTS.get(location.lower().strip(), None)
    if not districts:
        return [location]
    return [location] + districts[:MAX_DISTRICTS]
