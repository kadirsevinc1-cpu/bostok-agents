"""
Türkiye Ticaret ve Sanayi Odası Scraper
- Bilinen oda PDF listelerini indirir ve parse eder
- Her odanın sitesini tarayarak yeni PDF linklerini keşfeder
- pdfplumber ile email/telefon/firma adı çıkarır
- Lead olarak döndürür, 30 gün cache'ler
"""
import asyncio
import io
import json
import os
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests
from loguru import logger

_CACHE_FILE = Path("memory/tso_leads_cache.json")
_CACHE_TTL_DAYS = 30

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}")
PHONE_RE = re.compile(r"(?:\+90|0)\s*[\(\-]?\s*(\d{3})\s*[\)\-]?\s*(\d{3})\s*[\-]?\s*(\d{2})\s*[\-]?\s*(\d{2})")

_SKIP_EMAILS = {
    "noreply", "no-reply", "example", "test@", "@sentry", "wix", "wordpress",
    "squarespace", "schema", "w3.org", "placeholder", "domain.com", "@gmail.com",
    "@hotmail.com", "@yahoo", "bilgi@", "info@ito", "info@ato", "info@btso",
    "info@kto", "info@gto", "info@dto", "info@manisatso", "corlutso@",
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

# ─── Bilinen PDF Kaynakları ───────────────────────────────────────────────────

# (url, oda_adi, sehir)
KNOWN_PDF_SOURCES: list[tuple[str, str, str]] = [
    ("https://www.corlutso.org.tr/uploads/docs/corlutso_ihracatcilar.pdf", "Çorlu TSO", "Çorlu"),
]

# Keşfedilecek oda siteleri (DNS çalışanlar)
CHAMBER_SITES: list[tuple[str, str, str]] = [
    ("https://www.corlutso.org.tr", "Çorlu TSO", "Çorlu"),
    ("https://www.btso.org.tr", "Bursa TSO", "Bursa"),
    ("https://www.kto.org.tr", "Konya TO", "Konya"),
    ("https://www.gto.org.tr", "Gaziantep TO", "Gaziantep"),
    ("https://www.dto.org.tr", "Denizli TO", "Denizli"),
    ("https://www.manisatso.org.tr", "Manisa TSO", "Manisa"),
    ("https://www.ito.org.tr", "İstanbul TO", "Istanbul"),
    ("https://www.btso.org.tr", "Bursa TSO", "Bursa"),
]

# PDF URL'deki anahtar kelimeler — ihracat, üye listesi vb.
_PDF_KEYWORDS = [
    "ihracat", "uye", "üye", "firma", "liste", "katalog", "rehber",
    "sirket", "şirket", "member", "exporter", "directory",
]

# Sektör → Türkiye lokasyon eşleştirmesi
_TR_CITIES = {
    "istanbul", "ankara", "izmir", "bursa", "antalya", "adana", "konya",
    "gaziantep", "mersin", "kayseri", "samsun", "trabzon", "tekirdag",
    "tekirdag", "eskisehir", "denizli", "manisa", "sakarya", "kocaeli",
    "corlu", "çorlu", "gebze",
}


# ─── Cache ───────────────────────────────────────────────────────────────────

def _cache_key(source_url: str) -> str:
    return source_url.split("//", 1)[-1][:80]


def _get_cached(source_url: str):
    if not _CACHE_FILE.exists():
        return None
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        entry = data.get(_cache_key(source_url))
        if not entry:
            return None
        age = (datetime.now() - datetime.fromisoformat(entry["cached_at"])).days
        if age >= _CACHE_TTL_DAYS:
            return None
        return entry["leads"]
    except Exception:
        return None


def _set_cached(source_url: str, leads: list[dict]):
    _CACHE_FILE.parent.mkdir(exist_ok=True)
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8")) if _CACHE_FILE.exists() else {}
    except Exception:
        data = {}
    data[_cache_key(source_url)] = {
        "cached_at": datetime.now().isoformat(),
        "leads": leads,
    }
    tmp = _CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, _CACHE_FILE)


# ─── Email Doğrulama ─────────────────────────────────────────────────────────

def _valid_email(email: str) -> bool:
    e = email.lower()
    if any(s in e for s in _SKIP_EMAILS):
        return False
    domain = e.split("@", 1)[-1]
    if len(domain) < 4 or domain[0].isdigit():
        return False
    tld = "." + domain.rsplit(".", 1)[-1]
    if tld in {".png", ".jpg", ".gif", ".svg", ".webp"}:
        return False
    return True


# ─── PDF Parse ───────────────────────────────────────────────────────────────

def _parse_pdf_bytes(pdf_bytes: bytes, oda_adi: str, sehir: str) -> list[dict]:
    """PDF byte'larından firma listesini çıkar."""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber kurulu değil: pip install pdfplumber")
        return []

    leads = []
    seen_emails: set[str] = set()

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if not text.strip():
                    # Tablo olarak dene
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if not row:
                                continue
                            row_text = " ".join(str(c) for c in row if c)
                            text += row_text + "\n"

                emails = [e for e in EMAIL_RE.findall(text) if _valid_email(e) and e not in seen_emails]
                for email in emails:
                    seen_emails.add(email)
                    # Email'in yakınındaki satırdan firma adını çıkar
                    name = _extract_company_name_near_email(text, email)
                    phone = _extract_phone_near_email(text, email)
                    leads.append({
                        "email": email.lower(),
                        "name": name,
                        "phone": phone,
                        "location": sehir,
                        "source": f"TSO:{oda_adi}",
                    })

    except Exception as e:
        logger.warning(f"PDF parse hatası [{oda_adi}]: {e}")

    logger.info(f"TSO PDF parse: {len(leads)} email — {oda_adi}")
    return leads


def _extract_company_name_near_email(text: str, email: str) -> str:
    """Email adresinin bulunduğu satır veya önceki satırdan firma adı çıkar."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if email.lower() in line.lower():
            # Önce aynı satırı dene (tablo satırı olabilir)
            name = _clean_company_name(line.replace(email, ""))
            if len(name) > 4:
                return name
            # Önceki satıra bak
            if i > 0:
                name = _clean_company_name(lines[i - 1])
                if len(name) > 4:
                    return name
            # 2 önceki satıra bak
            if i > 1:
                name = _clean_company_name(lines[i - 2])
                if len(name) > 4:
                    return name
    return ""


def _clean_company_name(text: str) -> str:
    # Ortak Türk şirket eklerini içeren metni al
    text = re.sub(r"[|;,\t]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Sadece adres/telefon gibi görünen kısa parçaları at
    if re.search(r"^\d+|^(MAH|CAD|SK|NO|TEL|FAX|FAKS|E-MAIL|WWW)", text, re.I):
        return ""
    return text[:80]


def _extract_phone_near_email(text: str, email: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if email.lower() in line.lower():
            search_block = "\n".join(lines[max(0, i-2):i+3])
            m = PHONE_RE.search(search_block)
            if m:
                return "".join(m.groups())
    return ""


# ─── PDF Keşif ───────────────────────────────────────────────────────────────

def _discover_pdfs(base_url: str) -> list[str]:
    """Oda sitesini tarayarak üye/firma/ihracat PDF linklerini bul."""
    found = []
    try:
        session = requests.Session()
        session.headers.update(_HEADERS)

        # 1. Ana sayfa
        r = session.get(base_url, timeout=10)
        html = r.text

        # 2. Sitemap
        try:
            sm = session.get(base_url.rstrip("/") + "/sitemap.xml", timeout=6)
            if sm.status_code == 200:
                html += sm.text
        except Exception:
            pass

        # 3. Tüm PDF linkleri çıkar
        all_pdf_links = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html, re.I)

        # 4. İçerik URL'lerini de tara (ihracat/uye gibi)
        content_links = re.findall(
            r'href=["\']([^"\']*(?:ihracat|uye|üye|firma|liste|katalog|rehber|exporter|upload|doc)[^"\']*)["\']',
            html, re.I,
        )
        for link in content_links[:10]:
            full = _make_absolute(link, base_url)
            if full and not full.endswith(".pdf"):
                try:
                    sub = session.get(full, timeout=8)
                    sub_pdfs = re.findall(r'href=["\']([^"\']*\.pdf)["\']', sub.text, re.I)
                    all_pdf_links.extend(sub_pdfs)
                except Exception:
                    pass

        # 5. Filtrele — sadece ilgili keyword içerenler
        for link in all_pdf_links:
            link_lower = link.lower()
            if any(kw in link_lower for kw in _PDF_KEYWORDS):
                full = _make_absolute(link, base_url)
                if full and full not in found:
                    found.append(full)

    except Exception as e:
        logger.debug(f"PDF keşif hatası [{base_url}]: {e}")

    return found


def _make_absolute(link: str, base: str) -> str:
    if not link:
        return ""
    if link.startswith("http"):
        return link
    if link.startswith("//"):
        return "https:" + link
    base_parts = urllib.parse.urlparse(base)
    if link.startswith("/"):
        return f"{base_parts.scheme}://{base_parts.netloc}{link}"
    return f"{base.rstrip('/')}/{link.lstrip('/')}"


# ─── SerpAPI ile PDF Keşfi ───────────────────────────────────────────────────

_SERPAPI_QUERIES = [
    # Türkiye
    'site:*.org.tr filetype:pdf ihracatcilar email',
    'site:*.org.tr filetype:pdf "üye listesi" "e-mail"',
    'site:*.org.tr filetype:pdf "firma listesi" email',
    # Almanya — IHK
    'site:ihk*.de filetype:pdf "mitgliederliste" email',
    'site:*.ihk.de filetype:pdf "firmenverzeichnis" email',
    # İngiltere
    'site:*.chamber.co.uk filetype:pdf "member directory" email',
    'site:*.chamber.org.uk filetype:pdf "member list" email',
    # Fransa
    'site:cci*.fr filetype:pdf "annuaire" "email"',
    'site:*.cci.fr filetype:pdf "liste membres" email',
    # İtalya
    'site:*.camcom.it filetype:pdf "elenco imprese" email',
    # İspanya / Latin Amerika
    'site:*.camaras.org filetype:pdf "directorio" email',
    'filetype:pdf "camara de comercio" "directorio empresarial" email',
    # ABD
    'site:*.chamber.com filetype:pdf "member directory" email',
    'filetype:pdf "chamber of commerce" "member directory" email phone',
    # Genel global
    'filetype:pdf "exporters directory" email phone contact',
    'filetype:pdf "business directory" "chamber" email',
    'filetype:pdf "member list" "chamber of commerce" email',
]

_serpapi_discovered_key = "serpapi:discovered_pdfs"


def _serpapi_discover_pdfs() -> list[tuple[str, str, str]]:
    """SerpAPI veya Serper.dev ile Türkiye ticaret odası PDF'lerini bul."""
    cached = _get_cached(_serpapi_discovered_key)
    if cached is not None:
        logger.info(f"Search cache: {len(cached)} PDF linki")
        return [tuple(x) for x in cached]

    try:
        from config import settings
        serpapi_key = getattr(settings, "serpapi_api_key", "")
        serper_key = getattr(settings, "serper_api_key", "")
    except Exception:
        serpapi_key = serper_key = ""

    if not serpapi_key and not serper_key:
        return []

    results = []
    seen_urls: set[str] = set()

    for query in _SERPAPI_QUERIES:
        try:
            # Serper.dev önce (daha hızlı)
            if serper_key:
                r = requests.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                    json={"q": query, "num": 10, "hl": "tr", "gl": "tr"},
                    timeout=12,
                )
                if r.status_code == 200:
                    items = r.json().get("organic", [])
                    for item in items:
                        url = item.get("link", "")
                        if url.endswith(".pdf") and url not in seen_urls:
                            seen_urls.add(url)
                            domain = urllib.parse.urlparse(url).netloc
                            oda_adi = domain.replace("www.", "").split(".")[0].upper()
                            sehir, _ = _guess_location_from_domain(domain, url)
                            results.append((url, oda_adi, sehir))
                            logger.info(f"Serper PDF: {url} ({sehir})")
                    continue  # Serper başarılıysa SerpAPI'ye geçme

            # SerpAPI fallback
            if serpapi_key:
                r = requests.get(
                    "https://serpapi.com/search",
                    params={"q": query, "api_key": serpapi_key, "num": 10},
                    timeout=15,
                )
                if r.status_code == 200:
                    for item in r.json().get("organic_results", []):
                        url = item.get("link", "")
                        if url.endswith(".pdf") and url not in seen_urls:
                            seen_urls.add(url)
                            domain = urllib.parse.urlparse(url).netloc
                            oda_adi = domain.replace("www.", "").split(".")[0].upper()
                            sehir, _ = _guess_location_from_domain(domain, url)
                            results.append((url, oda_adi, sehir))
                            logger.info(f"SerpAPI PDF: {url} ({sehir})")
        except Exception as e:
            logger.debug(f"Arama hatası [{query}]: {e}")

    if results:
        _set_cached(_serpapi_discovered_key, results)
        logger.info(f"Arama toplam {len(results)} yeni PDF keşfetti")
    return results


def _guess_location_from_domain(domain: str, url: str = "") -> tuple[str, str]:
    """(şehir/ülke, ülke_kodu) döndür."""
    text = (domain + url).lower()

    # Türkiye şehirleri
    tr_cities = {
        "istanbul": "Istanbul", "ankara": "Ankara", "izmir": "Izmir",
        "bursa": "Bursa", "antalya": "Antalya", "konya": "Konya",
        "gaziantep": "Gaziantep", "denizli": "Denizli", "manisa": "Manisa",
        "samsun": "Samsun", "trabzon": "Trabzon", "adana": "Adana",
        "mersin": "Mersin", "kayseri": "Kayseri", "eskisehir": "Eskisehir",
        "corlu": "Çorlu", "tekirdag": "Tekirdağ", "sakarya": "Sakarya",
        "kocaeli": "Kocaeli", "gebze": "Gebze", "bursa": "Bursa",
    }
    for key, city in tr_cities.items():
        if key in text:
            return city, "TR"

    # TLD bazlı ülke tespiti
    tld_map = {
        ".org.tr": ("Türkiye", "TR"), ".com.tr": ("Türkiye", "TR"),
        ".de": ("Almanya", "DE"), ".co.uk": ("İngiltere", "UK"),
        ".org.uk": ("İngiltere", "UK"), ".fr": ("Fransa", "FR"),
        ".it": ("İtalya", "IT"), ".es": ("İspanya", "ES"),
        ".com.mx": ("Meksika", "MX"), ".com.ar": ("Arjantin", "AR"),
        ".com.br": ("Brezilya", "BR"), ".com.co": ("Kolombiya", "CO"),
        ".com.pe": ("Peru", "PE"), ".cl": ("Şili", "CL"),
        ".nl": ("Hollanda", "NL"), ".be": ("Belçika", "BE"),
        ".pl": ("Polonya", "PL"), ".pt": ("Portekiz", "PT"),
        ".gr": ("Yunanistan", "GR"), ".ro": ("Romanya", "RO"),
        ".ae": ("BAE", "AE"), ".sa": ("S.Arabistan", "SA"),
        ".com.au": ("Avustralya", "AU"), ".ca": ("Kanada", "CA"),
        ".co.za": ("G.Afrika", "ZA"), ".in": ("Hindistan", "IN"),
    }
    for tld, (country, code) in tld_map.items():
        if domain.endswith(tld):
            return country, code

    # Domain'de şehir ipucu
    global_cities = {
        "berlin": ("Berlin", "DE"), "hamburg": ("Hamburg", "DE"),
        "munich": ("Münih", "DE"), "frankfurt": ("Frankfurt", "DE"),
        "london": ("Londra", "UK"), "manchester": ("Manchester", "UK"),
        "paris": ("Paris", "FR"), "lyon": ("Lyon", "FR"),
        "milan": ("Milano", "IT"), "rome": ("Roma", "IT"),
        "madrid": ("Madrid", "ES"), "barcelona": ("Barcelona", "ES"),
        "amsterdam": ("Amsterdam", "NL"), "brussels": ("Brüksel", "BE"),
        "dubai": ("Dubai", "AE"), "abudhabi": ("Abu Dabi", "AE"),
        "newyork": ("New York", "US"), "losangeles": ("Los Angeles", "US"),
        "chicago": ("Chicago", "US"), "houston": ("Houston", "US"),
        "toronto": ("Toronto", "CA"), "sydney": ("Sidney", "AU"),
        "mumbai": ("Mumbai", "IN"), "delhi": ("Delhi", "IN"),
    }
    for key, (city, code) in global_cities.items():
        if key in text.replace("-", "").replace(".", ""):
            return city, code

    return "Global", "XX"


def _guess_city_from_domain(domain: str) -> str:
    city, _ = _guess_location_from_domain(domain)
    return city


# ─── PDF İndir ───────────────────────────────────────────────────────────────

def _download_pdf(url: str) -> bytes | None:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=30, stream=True)
        if r.status_code != 200:
            return None
        content_type = r.headers.get("content-type", "")
        if "pdf" not in content_type and not url.lower().endswith(".pdf"):
            return None
        data = b""
        for chunk in r.iter_content(chunk_size=65536):
            data += chunk
            if len(data) > 50 * 1024 * 1024:  # 50MB limit
                break
        return data if len(data) > 1000 else None
    except Exception as e:
        logger.debug(f"PDF indirme hatası [{url}]: {e}")
        return None


# ─── Ana Fonksiyonlar ─────────────────────────────────────────────────────────

def get_tso_leads_sync(sehir: str = "") -> list[dict]:
    """
    Tüm bilinen oda PDF kaynaklarından lead çek.
    sehir filtresi boşsa hepsini döndür.
    """
    all_leads: list[dict] = []

    # 1. Bilinen PDF'leri işle
    for pdf_url, oda_adi, oda_sehir in KNOWN_PDF_SOURCES:
        if sehir and oda_sehir.lower() not in sehir.lower() and sehir.lower() not in oda_sehir.lower():
            pass  # sehir filtresi — ama yine de al, email kaliteli

        cached = _get_cached(pdf_url)
        if cached is not None:
            logger.info(f"TSO cache: {len(cached)} lead — {oda_adi} (cache)")
            all_leads.extend(cached)
            continue

        logger.info(f"TSO PDF indiriliyor: {pdf_url}")
        pdf_bytes = _download_pdf(pdf_url)
        if not pdf_bytes:
            logger.warning(f"TSO PDF indirilemedi: {pdf_url}")
            continue

        leads = _parse_pdf_bytes(pdf_bytes, oda_adi, oda_sehir)
        _set_cached(pdf_url, leads)
        all_leads.extend(leads)

    # 2. SerpAPI ile yeni PDF'ler bul
    try:
        serpapi_pdfs = _serpapi_discover_pdfs()
        for pdf_url, oda_adi, oda_sehir in serpapi_pdfs:
            if any(pdf_url == known for known, _, _ in KNOWN_PDF_SOURCES):
                continue
            cached_leads = _get_cached(pdf_url)
            if cached_leads is not None:
                all_leads.extend(cached_leads)
                continue
            logger.info(f"SerpAPI PDF işleniyor: {pdf_url} ({oda_adi})")
            pdf_bytes = _download_pdf(pdf_url)
            if not pdf_bytes:
                continue
            leads = _parse_pdf_bytes(pdf_bytes, oda_adi, oda_sehir)
            if leads:
                _set_cached(pdf_url, leads)
                all_leads.extend(leads)
                KNOWN_PDF_SOURCES.append((pdf_url, oda_adi, oda_sehir))
    except Exception as e:
        logger.warning(f"SerpAPI keşif hatası: {e}")

    # 3. Oda sitelerini keşfet ve yeni PDF'ler bul
    for base_url, oda_adi, oda_sehir in CHAMBER_SITES:
        discover_key = f"discover:{base_url}"
        cached = _get_cached(discover_key)
        if cached is not None:
            already_known = [pdf_url for pdf_url, _, _ in KNOWN_PDF_SOURCES]
            new_pdfs = [p for p in cached if p not in already_known]
        else:
            logger.info(f"TSO keşif: {base_url}")
            new_pdfs = _discover_pdfs(base_url)
            _set_cached(discover_key, new_pdfs)

        for pdf_url in new_pdfs:
            # Zaten bilinen PDF ise atla
            if any(pdf_url == known for known, _, _ in KNOWN_PDF_SOURCES):
                continue

            cached_leads = _get_cached(pdf_url)
            if cached_leads is not None:
                all_leads.extend(cached_leads)
                continue

            logger.info(f"Yeni TSO PDF: {pdf_url} ({oda_adi})")
            pdf_bytes = _download_pdf(pdf_url)
            if not pdf_bytes:
                continue

            leads = _parse_pdf_bytes(pdf_bytes, oda_adi, oda_sehir)
            if leads:
                _set_cached(pdf_url, leads)
                all_leads.extend(leads)
                # Bilinen listeye ekle (oturum içi)
                KNOWN_PDF_SOURCES.append((pdf_url, oda_adi, oda_sehir))

    logger.info(f"TSO toplam: {len(all_leads)} lead (tüm odalar)")
    return all_leads


async def get_tso_leads(sehir: str = "") -> list[dict]:
    """Async wrapper."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_tso_leads_sync, sehir)
