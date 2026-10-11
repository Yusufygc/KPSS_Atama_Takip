"""KPSS Atama Takip - Asenkron Telegram Bildirim Servisi."""

from typing import Optional

import httpx

from app.config import settings
from app.core.constants.icons import PortalIcons, ScoreIcons
from app.core.constants.strings import MessageStrings, NotificationStrings
from app.core.exceptions.notification import TelegramDeliveryException
from app.core.logging import get_logger
from app.core.security import escape_html, is_http_url
from app.domain.models import Announcement
from app.infrastructure.notification.base import BaseNotifier

logger = get_logger("notification.telegram")


class TelegramNotifier(BaseNotifier):
    """Telegram Bot API üzerinden anlık bildirim gönderen servis."""

    channel_name = "telegram"

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        is_enabled: Optional[bool] = None,
    ) -> None:
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.is_enabled = (
            is_enabled if is_enabled is not None else settings.TELEGRAM_NOTIFICATIONS_ENABLED
        )

    @property
    def is_configured(self) -> bool:
        """Bot token ve Chat ID tanımlı mı kontrol eder."""
        return bool(self.bot_token and self.chat_id)

    def _redact(self, text: object) -> str:
        """Log ve hata metinlerinden bot token'ını temizler (token URL içinde taşınır)."""
        value = str(text)
        return value.replace(self.bot_token, "***") if self.bot_token else value

    def _format_announcement_message(self, item: Announcement) -> str:
        """İlan için zengin HTML Telegram mesaj metni üretir."""
        # Puan türü formatlama
        scores_str = escape_html(", ".join(s.value for s in item.matched_score_types) or "Genel")
        if item.has_p3_score:
            score_badge = f"[{scores_str} - Lisans] (Öncelikli {ScoreIcons.P3_PRIORITY})"
        elif item.has_career_score:
            score_badge = f"[{scores_str} - Kariyer {ScoreIcons.P1_CAREER}]"
        else:
            score_badge = f"[{scores_str}]"

        lines = [
            NotificationStrings.HEADER,
            "",
            NotificationStrings.INSTITUTION.format(institution=escape_html(item.institution)),
            NotificationStrings.POSITION.format(position=escape_html(item.title)),
            NotificationStrings.SCORE_TYPE.format(score_type=score_badge),
        ]

        if item.deadline_date:
            lines.append(NotificationStrings.DEADLINE.format(deadline=escape_html(item.deadline_date)))

        portal_icon = PortalIcons.get_for_portal(item.source_key)
        lines.append(
            NotificationStrings.SOURCE.format(
                source=f"{portal_icon} {escape_html(item.source_name)}"
            )
        )
        lines.append("")
        if item.source_key == "kamu_ilan_sbb":
            lines.append("🏛️ <b>Resmi Portal:</b> https://kamuilan.sbb.gov.tr/")
            lines.append("<i>ℹ️ Not: SBB doğrudan dış bağlantı erişimini engellemektedir. İlan PDF belgesine web dashboard üzerinden veya SBB ana sayfasından erişebilirsiniz.</i>")
        else:
            if is_http_url(item.url):
                lines.append(NotificationStrings.LINK.format(url=escape_html(item.url)))
            if item.pdf_url and item.pdf_url != item.url and is_http_url(item.pdf_url):
                lines.append(NotificationStrings.PDF_LINK.format(pdf_url=escape_html(item.pdf_url)))

        return "\n".join(lines)

    async def send_announcement(self, announcement: Announcement) -> bool:
        """Yeni bir ilanı Telegram kullanıcısına iletir."""
        if not self.is_enabled or not self.is_configured:
            logger.debug(MessageStrings.TELEGRAM_DISABLED)
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        message_text = self._format_announcement_message(announcement)

        payload = {
            "chat_id": self.chat_id,
            "text": message_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    logger.info(
                        MessageStrings.NOTIFICATION_SENT.format(title=announcement.title)
                    )
                    return True

                error_data = response.text
                logger.error(
                    f"Telegram API hatası ({response.status_code}): {self._redact(error_data)}"
                )
                raise TelegramDeliveryException(
                    original_error=self._redact(error_data), chat_id=self.chat_id
                )

        except Exception as e:
            logger.error(f"Telegram bildirimi gönderilemedi: {self._redact(e)}")
            return False

    async def test_connection(self) -> bool:
        """Telegram botu bağlantısını test mesajı atarak doğrular."""
        if not self.is_configured:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        test_msg = (
            "🔔 <b>KPSS Atama Takip Sistemi</b>\n\n"
            "✅ Telegram bildirim bağlantısı başarıyla kuruldu!\n"
            "Yeni bir atama veya personel alım ilanı yayınlandığında anında buradan haberdar edileceksiniz."
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": test_msg,
                        "parse_mode": "HTML",
                    },
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Telegram test mesajı gönderilemedi: {self._redact(e)}")
            return False
