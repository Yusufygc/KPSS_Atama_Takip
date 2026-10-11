"""Bildirim akışı: ilk çalıştırma tabanı, döngü başı sınır, özet, yeniden deneme ve Telegram HTTP davranışı."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.config import settings
from app.domain.models import Announcement, ScoreType
from app.domain.schemas import AnnouncementCreate, AnnouncementFilterParams, ScraperRunStatus
from app.infrastructure.database.repository import AnnouncementRepository
from app.infrastructure.notification import telegram as telegram_module
from app.infrastructure.notification.telegram import TelegramNotifier
from app.services.announcement_service import AnnouncementService


class FakeNotifier(TelegramNotifier):
    """Ağ çağrısı yapmayan, gönderimleri kaydeden bildirici."""

    def __init__(self, results=None):
        super().__init__(bot_token="1:abc", chat_id="1", is_enabled=True)
        self.sent_titles = []
        self.texts = []
        self._results = list(results) if results is not None else None

    async def send_announcement(self, announcement):
        ok = self._results.pop(0) if self._results else True
        if ok:
            self.sent_titles.append(announcement.title)
        else:
            self.attempted_failed = getattr(self, "attempted_failed", 0) + 1
        return ok

    async def send_text(self, text):
        self.texts.append(text)
        return True


class FakeOrchestrator:
    def __init__(self):
        self.dtos = []

    async def run_all(self):
        status = ScraperRunStatus(portal_key="fake", portal_name="Fake", status="success", found_count=len(self.dtos))
        return [("fake", list(self.dtos), status)]


def dto(title, url=None):
    return AnnouncementCreate(
        source_key="fake",
        source_name="Fake",
        title=title,
        institution="Kurum",
        url=url or f"https://example.test/{title.replace(' ', '-')}",
    )


@pytest.fixture(autouse=True)
def fast_notifications(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_SEND_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(settings, "TELEGRAM_MAX_PER_CYCLE", 15)
    monkeypatch.setattr(settings, "NOTIFY_ON_FIRST_RUN", False)
    monkeypatch.setattr(settings, "TELEGRAM_RETRY_WINDOW_HOURS", 24)


@pytest.fixture
def build(db_ready):
    def _build(notifier):
        orchestrator = FakeOrchestrator()
        service = AnnouncementService(AnnouncementRepository(), orchestrator, notifier)
        return service, orchestrator

    return _build


async def unnotified_count(service):
    _, total = await service.repository.list_announcements(AnnouncementFilterParams(only_unnotified=True))
    return total


async def seed(service, title="Mevcut ilan"):
    """Boş veritabanı olmasın diye bir kayıt ekler (ilk çalıştırma tabanını devre dışı bırakır)."""
    entity = Announcement(source_key="seed", source_name="Seed", title=title, institution="K", url="https://seed.test/1")
    entity.is_notified = True
    await service.repository.save(entity)


async def test_first_run_marks_existing_items_without_sending(build):
    notifier = FakeNotifier()
    service, orchestrator = build(notifier)
    orchestrator.dtos = [dto("A"), dto("B"), dto("C")]

    new_count, _ = await service.run_full_cycle()

    assert new_count == 3
    assert notifier.sent_titles == [] and notifier.texts == []
    assert await unnotified_count(service) == 0, "Mevcut ilanlar sessizce bildirildi sayılmalı"


async def test_first_run_can_notify_when_configured(build, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFY_ON_FIRST_RUN", True)
    notifier = FakeNotifier()
    service, orchestrator = build(notifier)
    orchestrator.dtos = [dto("A"), dto("B")]

    await service.run_full_cycle()
    assert sorted(notifier.sent_titles) == ["A", "B"]


async def test_new_items_after_first_run_are_notified_once(build):
    notifier = FakeNotifier()
    service, orchestrator = build(notifier)
    await seed(service)
    orchestrator.dtos = [dto("Yeni")]

    await service.run_full_cycle()
    await service.run_full_cycle()  # aynı ilan tekrar gelirse yeniden bildirilmez

    assert notifier.sent_titles == ["Yeni"]
    assert await unnotified_count(service) == 0


async def test_cap_sends_priority_items_then_one_summary(build, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_MAX_PER_CYCLE", 2)
    notifier = FakeNotifier()
    service, orchestrator = build(notifier)
    await seed(service)
    # P3 anahtar kelimeli ilan önce gönderilmeli
    orchestrator.dtos = [dto("Genel duyuru 1"), dto("Genel duyuru 2"), dto("Zabıta Memuru alımı"), dto("Genel duyuru 3")]

    await service.run_full_cycle()

    assert notifier.sent_titles[0] == "Zabıta Memuru alımı"
    assert len(notifier.sent_titles) == 2
    assert len(notifier.texts) == 1 and "2 ilan daha" in notifier.texts[0]
    assert await unnotified_count(service) == 0


async def test_failed_sends_are_retried_in_next_cycle(build):
    notifier = FakeNotifier(results=[False, True])
    service, orchestrator = build(notifier)
    await seed(service)
    orchestrator.dtos = [dto("Bir")]

    await service.run_full_cycle()
    assert notifier.sent_titles == [] and await unnotified_count(service) == 1

    orchestrator.dtos = []  # bu taramada yeni ilan yok; bekleyen yeniden denenmeli
    await service.run_full_cycle()
    assert notifier.sent_titles == ["Bir"] and await unnotified_count(service) == 0


async def test_aborts_after_consecutive_failures_and_skips_summary(build, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_MAX_PER_CYCLE", 4)
    notifier = FakeNotifier(results=[False] * 20)
    service, orchestrator = build(notifier)
    await seed(service)
    orchestrator.dtos = [dto(f"Ilan {i}") for i in range(8)]

    await service.run_full_cycle()

    assert notifier.attempted_failed == 2, "Art arda hatadan sonra gönderim bırakılmalı"
    assert notifier.texts == []
    assert await unnotified_count(service) == 8


async def test_items_older_than_retry_window_are_not_resent(build):
    notifier = FakeNotifier()
    service, orchestrator = build(notifier)
    await seed(service)
    old = Announcement(
        source_key="old", source_name="Old", title="Eski", institution="K", url="https://old.test/1",
        matched_score_types=[ScoreType.P3],
        created_at=(datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
    )
    await service.repository.save(old)

    await service.run_full_cycle()

    assert notifier.sent_titles == []
    assert await unnotified_count(service) == 1


# --- Telegram HTTP katmanı ---------------------------------------------------------


@pytest.fixture
def telegram_http(monkeypatch):
    """httpx isteklerini yakalayıp verilen yanıt listesini sırayla döndürür."""
    state = {"requests": [], "sleeps": []}

    def install(responses):
        queue = list(responses)

        def handler(request: httpx.Request):
            state["requests"].append(request)
            return queue.pop(0)

        real = httpx.AsyncClient
        monkeypatch.setattr(telegram_module.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))

        async def fake_sleep(seconds):
            state["sleeps"].append(seconds)

        monkeypatch.setattr(telegram_module.asyncio, "sleep", fake_sleep)
        return state

    return install


def notifier():
    return TelegramNotifier(bot_token="123:SECRET", chat_id="42", is_enabled=True)


async def test_telegram_waits_and_retries_once_on_rate_limit(telegram_http):
    state = telegram_http(
        [httpx.Response(429, json={"parameters": {"retry_after": 3}}), httpx.Response(200, json={"ok": True})]
    )
    assert await notifier().send_text("merhaba") is True
    assert len(state["requests"]) == 2
    assert state["sleeps"] and state["sleeps"][0] >= 3


async def test_telegram_gives_up_when_retry_after_is_too_long(telegram_http):
    state = telegram_http([httpx.Response(429, json={"parameters": {"retry_after": 600}})])
    assert await notifier().send_text("merhaba") is False
    assert len(state["requests"]) == 1 and state["sleeps"] == []


async def test_telegram_falls_back_to_plain_text_on_html_parse_error(telegram_http):
    state = telegram_http(
        [
            httpx.Response(400, json={"description": "Bad Request: can't parse entities: Unsupported start tag"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    assert await notifier().send_text("<b>kalın</b> &amp; metin") is True
    second = state["requests"][1].read().decode()
    assert "parse_mode" not in second and "<b>" not in second and "kalın" in second


async def test_telegram_does_not_loop_on_other_errors_and_never_logs_token(telegram_http, caplog):
    state = telegram_http([httpx.Response(401, json={"description": "Unauthorized bot123:SECRET"})])
    with caplog.at_level("ERROR"):
        assert await notifier().send_text("x") is False
    assert len(state["requests"]) == 1
    assert "SECRET" not in caplog.text


async def test_telegram_truncates_long_messages(telegram_http):
    state = telegram_http([httpx.Response(200, json={"ok": True})])
    assert await notifier().send_text("a" * 10000) is True
    import json

    text = json.loads(state["requests"][0].read())["text"]
    assert len(text) == 4096


async def test_expired_items_are_marked_notified_without_sending(build):
    from app.core.dates import today_in_turkey

    notifier = FakeNotifier()
    service, orchestrator = build(notifier)
    await seed(service)
    yesterday = (today_in_turkey() - timedelta(days=1)).strftime("%d.%m.%Y")
    tomorrow = (today_in_turkey() + timedelta(days=1)).strftime("%d.%m.%Y")
    expired = dto("Süresi dolmuş")
    expired.deadline_date = yesterday
    active = dto("Süresi var")
    active.deadline_date = tomorrow
    orchestrator.dtos = [expired, active]

    await service.run_full_cycle()

    assert notifier.sent_titles == ["Süresi var"]
    assert await unnotified_count(service) == 0


def test_telegram_message_shows_normalized_deadline():
    item = Announcement(
        source_key="x", source_name="K", title="T", institution="I", url="https://a.test",
        deadline_date="12 Ekim - 26 Ekim", created_at="2026-10-12T08:00:00+00:00",
    )
    assert "26.10.2026" in TelegramNotifier(bot_token="1:a", chat_id="1", is_enabled=True)._format_announcement_message(item)
