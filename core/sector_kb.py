"""
Sektör Bilgi Tabanı — başlangıçta LLM ile tohumlanır, gerçek etkileşimlerle büyür.
Agents doğrudan get_kb() üzerinden çağırır, mesaj kuyruğu gerektirmez.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from loguru import logger

KB_FILE = Path("memory/sector_kb.json")

# LLM ile tohumlanacak sektörler
SEED_SECTORS = [
    "restoran", "kafe", "diş kliniği", "güzellik salonu", "hukuk bürosu",
    "muhasebe bürosu", "inşaat", "gayrimenkul", "e-ticaret", "yazılım",
    "otel", "spor salonu", "özel okul", "sağlık kliniği", "oto galeri",
]

# Sabit dil kuralları — LLM'e bağımlı değil
LANG_RULES = {
    "tr": (
        "Türkçe yazım: 'Merhaba [isim],' ile başla. Kısa cümleler. "
        "İşletmenin adını kullan. Pratik faydayı vurgula. "
        "Resmi 'Siz' yerine samimi 'siz'. 'Saygılar' ile bitir."
    ),
    "en": (
        "English: Start with the business name, lead with value. "
        "Max 3 short paragraphs. Clear single CTA. No jargon, no buzzwords. "
        "Conversational but professional."
    ),
    "de": (
        "Deutsch: Formelle Anrede (Sie). Strukturiert und präzise. "
        "Datenschutz respektieren. Konkrete Vorteile mit Zahlen wenn möglich. "
        "Kein Amerikanismus, professionell aber zugänglich."
    ),
    "nl": (
        "Nederlands: Professioneel maar vriendelijk. U-vorm. "
        "Directe waardepropositie. Kort en bondig."
    ),
    "fr": (
        "Français: Vouvoiement (vous). Ton professionnel et chaleureux. "
        "Mise en valeur des bénéfices concrets. Formule de politesse finale."
    ),
}


class SectorKB:
    def __init__(self):
        self._data: dict = {
            "sectors": {},
            "patterns": {"positive": [], "negative": []},
            "meta": {"created_at": datetime.now().isoformat()},
        }
        self._load()

    # ── Okuma ──────────────────────────────────────────────────────

    def get_context(self, sector: str, location: str = "", lang: str = "tr") -> str:
        """Mail öncesi kullanılacak KB context'i — prompt'a eklenir."""
        parts = []

        lang_rule = LANG_RULES.get(lang, LANG_RULES["en"])
        parts.append(f"[Dil kuralı]\n{lang_rule}")

        sec = self._data["sectors"].get(self._norm(sector), {})
        if sec.get("context"):
            parts.append(f"[{sector} sektörü hakkında]\n{sec['context']}")

        pos = self._top_patterns("positive", sector, location, n=2)
        if pos:
            parts.append("[Bu sektörde işe yarayan]\n" + "\n".join(f"• {p}" for p in pos))

        neg = self._top_patterns("negative", sector, location, n=2)
        if neg:
            parts.append("[Kaçınılması gereken]\n" + "\n".join(f"• {p}" for p in neg))

        return "\n\n".join(parts)

    def get_summary(self, sector: str = "", location: str = "") -> str:
        total_sec = len(self._data["sectors"])
        total_pos = len(self._data["patterns"]["positive"])
        total_neg = len(self._data["patterns"]["negative"])
        lines = [
            f"📚 <b>KB Özeti:</b> {total_sec} sektör, "
            f"{total_pos} pozitif, {total_neg} negatif pattern"
        ]
        pos = self._top_patterns("positive", sector, location, n=5)
        if pos:
            lines.append("\n✅ <b>İşe yarar:</b>\n" + "\n".join(f"  • {p}" for p in pos))
        neg = self._top_patterns("negative", sector, location, n=3)
        if neg:
            lines.append("\n❌ <b>Kaçın:</b>\n" + "\n".join(f"  • {p}" for p in neg))
        return "\n".join(lines)

    def sector_info(self, sector: str) -> str:
        sec = self._data["sectors"].get(self._norm(sector), {})
        if not sec:
            return f"'{sector}' için henüz bilgi yok."
        ctx = sec.get("context", "Bilgi yok")
        updated = sec.get("updated_at", sec.get("seeded_at", ""))[:10]
        pos = self._top_patterns("positive", sector, n=3)
        neg = self._top_patterns("negative", sector, n=2)
        parts = [f"<b>{sector}</b> (güncellendi: {updated})\n\n{ctx}"]
        if pos:
            parts.append("✅ İşe yarar:\n" + "\n".join(f"• {p}" for p in pos))
        if neg:
            parts.append("❌ Kaçın:\n" + "\n".join(f"• {p}" for p in neg))
        return "\n\n".join(parts)

    def needs_seeding(self, sector: str) -> bool:
        sec = self._data["sectors"].get(self._norm(sector), {})
        return not sec.get("seeded") and not sec.get("context")

    # ── Yazma ──────────────────────────────────────────────────────

    def mark_seeded(self, sector: str, context: str):
        key = self._norm(sector)
        entry = self._data["sectors"].setdefault(key, {})
        entry["context"] = context[:700]
        entry["seeded"] = True
        entry["seeded_at"] = datetime.now().isoformat()
        self._save()

    def add_knowledge(self, sector: str, knowledge: str):
        """Kullanıcı /ogret komutuyla bilgi ekler."""
        key = self._norm(sector)
        entry = self._data["sectors"].setdefault(key, {"seeded": False})
        existing = entry.get("context", "")
        if knowledge.strip() not in existing:
            entry["context"] = (existing + "\n• " + knowledge.strip()).strip()
            entry["updated_at"] = datetime.now().isoformat()
            self._save()
            logger.info(f"KB bilgi eklendi: {sector}")

    def add_pattern(self, outcome: str, sector: str, location: str, lang: str, description: str):
        """Gerçek etkileşimden öğrenilen pattern."""
        key = "positive" if outcome == "positive" else "negative"
        patterns = self._data["patterns"][key]
        for p in patterns:
            if p["sector"] == self._norm(sector) and p["description"][:40] == description[:40]:
                p["count"] = p.get("count", 1) + 1
                p["last_seen"] = datetime.now().isoformat()
                self._save()
                return
        patterns.append({
            "sector": self._norm(sector),
            "location": location.lower(),
            "lang": lang,
            "description": description[:250],
            "count": 1,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
        })
        self._data["patterns"][key] = patterns[-300:]
        self._save()
        logger.info(f"KB pattern [{outcome}]: {sector}/{location}")

    # ── Yardımcılar ────────────────────────────────────────────────

    def _top_patterns(self, outcome: str, sector: str = "", location: str = "", n: int = 3) -> list[str]:
        patterns = self._data["patterns"].get(outcome, [])
        scored = []
        for p in patterns:
            score = p.get("count", 1)
            if sector and sector.lower()[:8] in p.get("sector", ""):
                score += 5
            if location and location.lower()[:6] in p.get("location", ""):
                score += 3
            scored.append((score, p["description"]))
        scored.sort(reverse=True)
        return [d for _, d in scored[:n]]

    def _norm(self, s: str) -> str:
        return s.lower().strip().replace(" ", "_")[:40]

    def _save(self):
        KB_FILE.parent.mkdir(exist_ok=True)
        tmp = KB_FILE.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, KB_FILE)
        except Exception as e:
            logger.warning(f"SectorKB save error: {e}")

    def _load(self):
        if not KB_FILE.exists():
            return
        try:
            self._data = json.loads(KB_FILE.read_text(encoding="utf-8"))
            logger.info(f"SectorKB: {len(self._data['sectors'])} sektör, "
                        f"{len(self._data['patterns']['positive'])} pozitif pattern yüklendi")
        except Exception as e:
            logger.warning(f"SectorKB load error: {e}")


_kb = SectorKB()


def get_kb() -> SectorKB:
    return _kb
