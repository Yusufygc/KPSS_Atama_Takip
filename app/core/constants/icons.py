"""KPSS Atama Takip - Merkezi İkon ve Emoji Tanımları."""


class StatusIcons:
    """Sistem durumu ve bildirim simgeleri."""

    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    RUNNING = "⏳"
    IDLE = "💤"
    BELL = "🔔"
    CALENDAR = "📅"
    LINK = "🔗"
    DOCUMENT = "📄"
    CITY = "📍"


class ScoreIcons:
    """KPSS puan türü simgeleri."""

    P3_PRIORITY = "🎓"  # Lisans B Grubu (Öncelikli)
    P1_CAREER = "🎯"    # Kariyer / Uzman / Müfettiş
    P2_CAREER = "🏛"    # Kariyer / Denetçi / Kurul
    GENERAL = "📋"


class PortalIcons:
    """Portalların ayırt edici simgeleri."""

    KARIYER_KAPISI = "💼"
    RESMI_GAZETE = "📜"
    KAMU_ILAN_SBB = "🏛"
    YEREL_YONETIMLER = "🏙"
    ISKUR = "🏢"
    ILAN_GOV_TR = "📰"
    DEFAULT = "🌐"

    @classmethod
    def get_for_portal(cls, portal_key: str) -> str:
        """Portal anahtarına karşılık gelen ikonu döner."""
        mapping = {
            "kariyer_kapisi": cls.KARIYER_KAPISI,
            "resmi_gazete": cls.RESMI_GAZETE,
            "kamu_ilan_sbb": cls.KAMU_ILAN_SBB,
            "yerel_yonetimler": cls.YEREL_YONETIMLER,
            "iskur": cls.ISKUR,
            "ilan_gov_tr": cls.ILAN_GOV_TR,
        }
        return mapping.get(portal_key, cls.DEFAULT)
