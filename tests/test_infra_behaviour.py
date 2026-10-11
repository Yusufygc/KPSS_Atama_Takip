"""İstek yeniden deneme, zamanlayıcı, toplu ekleme ve küçük API davranışları."""

import time

import httpx
import pytest

from app.config import settings
from app.core.exceptions.scraper import NetworkScraperException
from app.domain.models import Announcement, ScoreType
from app.infrastructure.database.repository import AnnouncementRepository
from app.infrastructure.notification.telegram import TelegramNotifier
from app.scrapers import base as base_module
from app.scrapers.base import BaseScraper
from app.services.scheduler import SchedulerService


class DummyScraper(BaseScraper):
    portal_key = "dummy"
    portal_name = "Dummy"

    async def scrape(self):
        return []


@pytest.fixture
def mock_http(monkeypatch):
    """base.py içindeki httpx istemcisini sahte transport ile değiştirir; istek ve bekleme kayıtlarını tutar."""
    state = {"requests": 0, "sleeps": []}

    def install(*responses):
        queue = list(responses)

        def handler(request):
            state["requests"] += 1
            return queue.pop(0) if len(queue) > 1 else queue[0]

        real = httpx.AsyncClient
        monkeypatch.setattr(base_module.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))

        async def fake_sleep(seconds):
            state["sleeps"].append(seconds)

        monkeypatch.setattr(base_module.asyncio, "sleep", fake_sleep)
        return state

    return install


async def test_permanent_client_errors_are_not_retried(mock_http):
    state = mock_http(httpx.Response(404))
    with pytest.raises(NetworkScraperException) as exc:
        await DummyScraper()._request("GET", "https://example.test/yok")
    assert state["requests"] == 1 and exc.value.status_code == 404


async def test_server_errors_are_retried_then_raise(mock_http):
    state = mock_http(httpx.Response(503))
    with pytest.raises(NetworkScraperException):
        await DummyScraper()._request("GET", "https://example.test/x", retries=3)
    assert state["requests"] == 3


async def test_transient_server_error_then_success(mock_http):
    state = mock_http(httpx.Response(502), httpx.Response(200, text="tamam"))
    response = await DummyScraper()._request("GET", "https://example.test/x")
    assert response.text == "tamam" and state["requests"] == 2


async def test_rate_limit_waits_retry_after_even_if_header_is_http_date(mock_http):
    state = mock_http(
        httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}),
        httpx.Response(200, text="ok"),
    )
    response = await DummyScraper()._request("GET", "https://example.test/x")
    assert response.text == "ok"
    assert state["sleeps"] == [5], "HTTP-date biçimi çökmemeli, varsayılan bekleme kullanılmalı"


@pytest.mark.parametrize(("value", "expected"), [("7", 7), (None, 5), ("abc", 5), ("9999", 60), ("-3", 0)])
def test_parse_retry_after(value, expected):
    assert BaseScraper._parse_retry_after(value) == expected


async def test_scheduler_schedules_startup_scan_without_pausing_the_job(monkeypatch):
    for run_on_startup in (True, False):
        service = SchedulerService(service=object())
        monkeypatch.setattr(settings, "SCRAPER_RUN_ON_STARTUP", run_on_startup)
        service.start()
        try:
            job = service.scheduler.get_job("periodic_scraper_job")
            assert job.next_run_time is not None, "İş duraklatılmış olmamalı"
            if run_on_startup:
                assert job.next_run_time.timestamp() - time.time() < settings.SCRAPER_STARTUP_DELAY_SECONDS + 5
        finally:
            service.stop()


async def test_insert_new_returns_only_new_items_with_ids(db_ready):
    repo = AnnouncementRepository()

    def item(title):
        return Announcement(source_key="s", source_name="S", title=title, institution="K", url=f"https://a.test/{title}", matched_score_types=[ScoreType.P3])

    first = await repo.insert_new([item("A"), item("B")])
    assert [i.title for i in first] == ["A", "B"] and all(i.id for i in first)

    second = await repo.insert_new([item("B"), item("C")])
    assert [i.title for i in second] == ["C"]
    assert await repo.insert_new([]) == []


async def test_search_text_length_is_limited(client):
    assert (await client.get("/api/announcements?search=" + "a" * 101)).status_code == 422
    assert (await client.get("/api/announcements?search=" + "a" * 100)).status_code == 200


def test_telegram_message_prefers_position_over_full_title():
    item = Announcement(
        source_key="x", source_name="K", title="KURUM - 5 Yazılım Mühendisi", institution="KURUM",
        position="5 Yazılım Mühendisi", url="https://a.test",
    )
    text = TelegramNotifier(bot_token="1:a", chat_id="1", is_enabled=True)._format_announcement_message(item)
    assert "5 Yazılım Mühendisi" in text and "KURUM - 5" not in text
