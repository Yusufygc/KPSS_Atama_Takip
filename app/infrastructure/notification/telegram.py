"""KPSS Atama Takip - Asenkron Telegram Bildirim Servisi."""

import asyncio
import html
import re
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.core.constants.icons import PortalIcons, ScoreIcons
from app.core.constants.settings import TelegramConstants
from app.core.constants.strings import MessageStrings, NotificationStrings
from app.core.logging import get_logger
from app.core.security import escape_html, is_http_url
from app.domain.models import Announcement
from app.infrastructure.notification.base import BaseNotifier

logger = get_logger("notification.telegram")

_TAG_RE = re.compile(r"<[^>]+>")


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

    @property
    def is_ready(self) -> bool:
        """Bildirim gönderilebilir durumda mı (açık ve yapılandırılmış)."""
        return self.is_enabled and self.is_configured

    def _redact(self, text: object) -> str:
        """Log ve hata metinlerinden bot token'ını temizler (token URL içinde taşınır)."""
        value = str(text)
        return value.replace(self.bot_token, "***") if self.bot_token else value

    @staticmethod
    def _format_deadline(item: Announcement) -> str:
        """Normalize tarih varsa GG.AA.YYYY, yoksa kaynaktaki ham metni döner."""
        if item.deadline_on:
            year, month, day = item.deadline_on.split("-")
            return f"{day}.{month}.{year}"
        return item.deadline_date or ""

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

        deadline_text = self._format_deadline(item)
        if deadline_text:
            lines.append(NotificationStrings.DEADLINE.format(deadline=escape_html(deadline_text)))

        portal_icon = PortalIcons.get_for_portal(item.source_key)
        lines.append(
            NotificationStrings.SOURCE.format(
                source=f"{portal_icon} {escape_html(item.source_name)}"
            )
        )
        lines.append("")
        if item.source_key == "kamu_ilan_sbb":
            lines.append(NotificationStrings.SBB_PORTAL_LINE)
            lines.append(NotificationStrings.SBB_PORTAL_NOTE)
        else:
            if is_http_url(item.url):
                lines.append(NotificationStrings.LINK.format(url=escape_html(item.url)))
            if item.pdf_url and item.pdf_url != item.url and is_http_url(item.pdf_url):
                lines.append(NotificationStrings.PDF_LINK.format(pdf_url=escape_html(item.pdf_url)))

        return "\n".join(lines)

    @staticmethod
    def _error_body(response: httpx.Response) -> Dict[str, Any]:
        """Telegram hata yanıtını sözlüğe çevirir (JSON değilse boş sözlük)."""
        try:
            body = response.json()
            return body if isinstance(body, dict) else {}
        except ValueError:
            return {}

    async def _post_message(self, text: str, parse_mode: Optional[str] = "HTML") -> bool:
        """Mesajı gönderir; hız sınırında (429) bekleyip bir kez yeniden dener,
        HTML ayrıştırma hatasında düz metne düşer. Başarılıysa True döner."""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        text = text[: TelegramConstants.MAX_MESSAGE_LENGTH]
        rate_limit_retried = False

        for _ in range(TelegramConstants.MAX_SEND_ATTEMPTS):
            payload: Dict[str, Any] = {"chat_id": self.chat_id, "text": text}
            if parse_mode:
                payload["parse_mode"] = parse_mode

            try:
                async with httpx.AsyncClient(timeout=TelegramConstants.REQUEST_TIMEOUT_SECONDS) as client:
                    response = await client.post(url, json=payload)
            except httpx.HTTPError as exc:
                logger.error(f"Telegram bildirimi gönderilemedi: {self._redact(exc)}")
                return False

            if response.status_code == 200:
                return True

            body = self._error_body(response)
            description = str(body.get("description", ""))

            if response.status_code == 429 and not rate_limit_retried:
                retry_after = int((body.get("parameters") or {}).get("retry_after", 1))
                if retry_after > TelegramConstants.MAX_RETRY_AFTER_SECONDS:
                    logger.error(f"Telegram hız sınırı çok uzun ({retry_after} sn), gönderim ertelendi.")
                    return False
                logger.warning(f"Telegram hız sınırı (429): {retry_after} sn bekleniyor...")
                rate_limit_retried = True
                await asyncio.sleep(retry_after + 0.5)
                continue

            if response.status_code == 400 and parse_mode and "parse entities" in description:
                logger.warning("Telegram HTML ayrıştırma hatası, düz metinle yeniden deneniyor.")
                text = html.unescape(_TAG_RE.sub("", text))
                parse_mode = None
                continue

            logger.error(
                f"Telegram API hatası ({response.status_code}): {self._redact(description or response.text)}"
            )
            return False

        return False

    async def send_announcement(self, announcement: Announcement) -> bool:
        """Yeni bir ilanı Telegram kullanıcısına iletir."""
        if not self.is_ready:
            logger.debug(MessageStrings.TELEGRAM_DISABLED)
            return False

        sent = await self._post_message(self._format_announcement_message(announcement))
        if sent:
            logger.info(MessageStrings.NOTIFICATION_SENT.format(title=announcement.title))
        return sent

    async def send_text(self, text: str) -> bool:
        """Serbest HTML metin (özet/duyuru) gönderir."""
        if not self.is_ready:
            return False
        return await self._post_message(text)

    async def test_connection(self) -> bool:
        """Telegram botu bağlantısını test mesajı atarak doğrular."""
        if not self.is_configured:
            return False
        return await self._post_message(NotificationStrings.TEST_MESSAGE)
