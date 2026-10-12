"""Gözetimsiz çalışma: günlük yedek, yedek saklama ve portal arıza uyarıları."""

import sqlite3

import pytest

from app.config import settings
from app.domain.models import Announcement, ScoreType
from app.domain.schemas import ScraperRunStatus
from app.infrastructure.database.repository import AnnouncementRepository
from app.infrastructure.notification.telegram import TelegramNotifier
from app.services.announcement_service import AnnouncementService
from app.services.backup import BACKUP_PREFIX, backup_database
from app.services.scheduler import SchedulerService

# ---------------- yedekleme ----------------


@pytest.fixture
def backup_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DB_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)  # mutlak yedek yolu BASE_DIR ile birleşir
    return tmp_path / "backups"


async def test_backup_is_a_consistent_readable_copy(db_ready, backup_dir):
    repo = AnnouncementRepository()
    await repo.save(Announcement(source_key="s", source_name="S", title="Yedeklenecek", institution="K", url="https://a.test/1", matched_score_types=[ScoreType.P3]))

    path = await backup_database()

    assert path.parent == backup_dir and path.name.startswith(BACKUP_PREFIX)
    assert not list(backup_dir.glob("*.tmp")), "Yarım/geçici dosya kalmamalı"
    copy = sqlite3.connect(path)
    try:
        assert copy.execute("SELECT title FROM announcements").fetchall() == [("Yedeklenecek",)]
        assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        copy.close()


async def test_backup_works_while_another_connection_is_writing(db_ready, backup_dir):
    live = sqlite3.connect(settings.resolved_database_path)
    live.execute("BEGIN IMMEDIATE")  # açık yazma işlemi (WAL: okuyucuyu engellemez)
    try:
        path = await backup_database()
    finally:
        live.rollback()
        live.close()
    assert path.exists()


async def test_backup_keeps_only_the_newest_n(db_ready, backup_dir, monkeypatch):
    monkeypatch.setattr(settings, "DB_BACKUP_KEEP", 3)
    backup_dir.mkdir(parents=True)
    for day in range(1, 7):
        (backup_dir / f"{BACKUP_PREFIX}202610{day:02d}_040000.db").write_bytes(b"x")

    newest = await backup_database()

    names = sorted(p.name for p in backup_dir.glob(f"{BACKUP_PREFIX}*.db"))
    assert len(names) == 3 and newest.name in names
    assert f"{BACKUP_PREFIX}20261001_040000.db" not in names, "En eski yedekler silinmeli"


async def test_scheduler_registers_daily_backup_job_only_when_enabled(monkeypatch):
    for enabled in (True, False):
        monkeypatch.setattr(settings, "DB_BACKUP_ENABLED", enabled)
        service = SchedulerService(service=object())
        service.start()
        try:
            job = service.scheduler.get_job("daily_db_backup_job")
            assert (job is not None) is enabled
            assert service.scheduler.get_job("periodic_scraper_job") is not None
        finally:
            service.stop()


# ---------------- portal arıza uyarıları ----------------


class RecordingNotifier(TelegramNotifier):
    def __init__(self, send_ok=True):
        super().__init__(bot_token="1:abc", chat_id="1", is_enabled=True)
        self.texts = []
        self.send_ok = send_ok

    async def send_announcement(self, announcement):
        return True

    async def send_text(self, text):
        if self.send_ok:
            self.texts.append(text)
        return self.send_ok


class ScriptedOrchestrator:
    """Her çağrıda sıradaki durum listesini döner."""

    def __init__(self, script):
        self.script = list(script)

    async def run_all(self):
        outcome = self.script.pop(0)
        return [
            (key, [], ScraperRunStatus(portal_key=key, portal_name=name, status=status, error_message=error))
            for key, name, status, error in outcome
        ]


FAIL = [("iskur", "İŞKUR", "error", "Bağlantı zaman aşımı <b>")]
OK = [("iskur", "İŞKUR", "success", None)]


def make_service(script, notifier):
    return AnnouncementService(AnnouncementRepository(), ScriptedOrchestrator(script), notifier)


async def test_alert_after_threshold_is_sent_once_then_recovery_once(db_ready, monkeypatch):
    monkeypatch.setattr(settings, "PORTAL_FAILURE_ALERT_THRESHOLD", 3)
    notifier = RecordingNotifier()
    service = make_service([FAIL, FAIL, FAIL, FAIL, FAIL, OK, OK], notifier)

    for _ in range(2):
        await service.run_full_cycle()
    assert notifier.texts == [], "Eşikten önce uyarı gönderilmemeli"

    await service.run_full_cycle()
    assert len(notifier.texts) == 1 and "Portal arızası" in notifier.texts[0] and "İŞKUR" in notifier.texts[0]
    assert "<b>" not in notifier.texts[0].split("Hata:")[1], "Hata metni HTML kaçışlanmalı"

    for _ in range(2):
        await service.run_full_cycle()
    assert len(notifier.texts) == 1, "Aynı arıza için tekrar uyarı gönderilmemeli"

    await service.run_full_cycle()
    assert len(notifier.texts) == 2 and "yeniden çalışıyor" in notifier.texts[1]

    await service.run_full_cycle()
    assert len(notifier.texts) == 2, "Toparlanma mesajı da yalnızca bir kez gönderilmeli"


async def test_alert_rearms_after_recovery(db_ready, monkeypatch):
    monkeypatch.setattr(settings, "PORTAL_FAILURE_ALERT_THRESHOLD", 2)
    notifier = RecordingNotifier()
    service = make_service([FAIL, FAIL, OK, FAIL, FAIL], notifier)
    for _ in range(5):
        await service.run_full_cycle()
    kinds = ["arıza" if "arızası" in t else "düzeldi" for t in notifier.texts]
    assert kinds == ["arıza", "düzeldi", "arıza"]


async def test_failed_alert_delivery_is_retried_next_cycle(db_ready, monkeypatch):
    monkeypatch.setattr(settings, "PORTAL_FAILURE_ALERT_THRESHOLD", 1)
    notifier = RecordingNotifier(send_ok=False)
    service = make_service([FAIL, FAIL], notifier)

    await service.run_full_cycle()
    assert notifier.texts == []
    notifier.send_ok = True
    await service.run_full_cycle()
    assert len(notifier.texts) == 1, "Gönderilemeyen uyarı sonraki taramada yeniden denenmeli"


async def test_alerts_can_be_disabled(db_ready, monkeypatch):
    monkeypatch.setattr(settings, "PORTAL_FAILURE_ALERT_THRESHOLD", 0)
    notifier = RecordingNotifier()
    service = make_service([FAIL] * 5, notifier)
    for _ in range(5):
        await service.run_full_cycle()
    assert notifier.texts == []
