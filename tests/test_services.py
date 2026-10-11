"""Telegram biçimlendirme/güvenlik ve tarama servisi davranışları."""

import asyncio

import pytest

from app.core.exceptions.scraper import ScrapeInProgressException
from app.domain.models import Announcement, ScoreType
from app.domain.schemas import AnnouncementCreate, AnnouncementFilterParams, ScraperRunStatus
from app.infrastructure.database.repository import AnnouncementRepository
from app.infrastructure.notification.telegram import TelegramNotifier
from app.services.announcement_service import AnnouncementService


def test_telegram_message_escapes_scraped_content():
    notifier = TelegramNotifier(bot_token="1:abc", chat_id="1", is_enabled=True)
    item = Announcement(
        source_key="x",
        source_name="<b>Kaynak</b>",
        title="<script>alert(1)</script> & İlan",
        institution='Kurum "<i>"',
        url='https://example.test/a?x=1&y="2"',
        pdf_url="https://example.test/a.pdf",
        deadline_date="<u>bugün</u>",
        matched_score_types=[ScoreType.P3],
    )
    text = notifier._format_announcement_message(item)

    assert "<script>" not in text and "<i>" not in text and "<u>" not in text
    assert "&lt;script&gt;" in text
    assert 'href="https://example.test/a?x=1&amp;y=&quot;2&quot;"' in text


def test_telegram_message_drops_non_http_links():
    notifier = TelegramNotifier(bot_token="1:abc", chat_id="1", is_enabled=True)
    item = Announcement(
        source_key="x", source_name="K", title="T", institution="I", url="javascript:alert(1)"
    )
    assert "javascript:" not in notifier._format_announcement_message(item)


def test_telegram_redacts_token():
    notifier = TelegramNotifier(bot_token="123:SECRET", chat_id="1", is_enabled=True)
    assert "SECRET" not in notifier._redact("hata: https://api.telegram.org/bot123:SECRET/sendMessage")


class FakeOrchestrator:
    def __init__(self, dtos, gate=None):
        self.dtos = dtos
        self.gate = gate

    async def run_all(self):
        if self.gate:
            await self.gate.wait()
        status = ScraperRunStatus(portal_key="fake", portal_name="Fake", status="success", found_count=len(self.dtos))
        return [("fake", self.dtos, status)]


def dto(**kw):
    base = {"source_key": "fake", "source_name": "Fake", "title": "Mühendis Alımı", "institution": "Kurum"}
    base.update(kw)
    return AnnouncementCreate(**base)


async def test_cycle_skips_items_with_unsafe_urls_and_strips_bad_pdf_url(db_ready):
    service = AnnouncementService(
        repository=AnnouncementRepository(),
        orchestrator=FakeOrchestrator(
            [
                dto(title="Güvenli", url="https://example.test/1", pdf_url="javascript:alert(1)"),
                dto(title="Zararlı", url="javascript:alert(1)"),
            ]
        ),
        notifier=TelegramNotifier(is_enabled=False),
    )
    new_count, _ = await service.run_full_cycle()
    assert new_count == 1

    items, total = await service.repository.list_announcements(AnnouncementFilterParams())
    assert total == 1
    assert items[0].title == "Güvenli" and items[0].pdf_url is None


async def test_cycle_rejects_overlapping_runs(db_ready):
    gate = asyncio.Event()
    service = AnnouncementService(
        repository=AnnouncementRepository(),
        orchestrator=FakeOrchestrator([], gate),
        notifier=TelegramNotifier(is_enabled=False),
    )
    running = asyncio.create_task(service.run_full_cycle())
    await asyncio.sleep(0.05)
    assert service.is_scraping
    with pytest.raises(ScrapeInProgressException):
        await service.run_full_cycle()

    gate.set()
    await running
    assert not service.is_scraping
