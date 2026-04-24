"""
Agent Bilgi Tabanı — AGENTS.md ve şablonları yükler.
Her agent başlarken bu modülü kullanarak bilgi tabanına erişir.
"""
from pathlib import Path
from loguru import logger

BASE_DIR      = Path(__file__).parent.parent
AGENTS_MD     = BASE_DIR / "AGENTS.md"
TEMPLATES_DIR = BASE_DIR / "templates"
ERROR_LOG_MARKER = "## Hata Logu"


def get_agent_instructions() -> str:
    """AGENTS.md içeriğini döndür — tüm agent'ların sistem promptuna eklenir."""
    if not AGENTS_MD.exists():
        return ""
    return AGENTS_MD.read_text(encoding="utf-8")


def get_template(template_name: str) -> str:
    """Şablon HTML'ini döndür. Örn: get_template('restoran')"""
    path = TEMPLATES_DIR / f"{template_name}.html"
    if not path.exists():
        available = [f.stem for f in TEMPLATES_DIR.glob("*.html")]
        logger.warning(f"Şablon bulunamadı: {template_name}. Mevcut: {available}")
        return ""
    return path.read_text(encoding="utf-8")


def list_templates() -> list[str]:
    """Mevcut şablon adlarını listele."""
    return [f.stem for f in TEMPLATES_DIR.glob("*.html")]


def detect_template(brief: str) -> str:
    """Brief'e göre en uygun şablonu seç."""
    brief_lower = brief.lower()
    if any(w in brief_lower for w in ["restoran", "kafe", "cafe", "yemek", "mutfak", "pizza", "burger"]):
        return "restoran"
    if any(w in brief_lower for w in ["e-ticaret", "eticaret", "mağaza", "shop", "ürün", "satış"]):
        return "eticaret"
    if any(w in brief_lower for w in ["landing", "kampanya", "tek sayfa", "tanıtım"]):
        return "landing"
    return "kurumsal"


def log_error(agent: str, error: str, solution: str):
    """Hatayı AGENTS.md'ye kaydet — gelecekte tekrarlanmasın."""
    if not AGENTS_MD.exists():
        return
    content = AGENTS_MD.read_text(encoding="utf-8")
    from datetime import date
    entry = f"\n- [{date.today()}] [{agent}] {error[:100]} → {solution[:150]}"
    if ERROR_LOG_MARKER in content:
        content = content.replace(ERROR_LOG_MARKER, ERROR_LOG_MARKER + entry)
        AGENTS_MD.write_text(content, encoding="utf-8")
        logger.info(f"Hata logu güncellendi: {agent}")


def log_success(pattern: str, description: str):
    """Başarılı çözümü AGENTS.md'ye ekle."""
    if not AGENTS_MD.exists():
        return
    content = AGENTS_MD.read_text(encoding="utf-8")
    entry = f"\n- {pattern}: {description}"
    marker = "## Başarılı Çözümler"
    if marker in content:
        content = content.replace(marker, marker + entry, 1)
        AGENTS_MD.write_text(content, encoding="utf-8")
