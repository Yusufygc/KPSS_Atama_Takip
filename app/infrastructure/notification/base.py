"""KPSS Atama Takip - Bildirim Dağıtıcı Temel Arayüzü."""

from abc import ABC, abstractmethod
from app.domain.models import Announcement


class BaseNotifier(ABC):
    """Tüm bildirim kanallarının (Telegram, E-posta, vb.) uygulayacağı soyut arayüz."""

    channel_name: str

    @abstractmethod
    async def send_announcement(self, announcement: Announcement) -> bool:
        """Yeni bir ilanı kullanıcıya iletir. Başarılıysa True döner."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Bildirim kanalının bağlantısını ve ayarlarını test eder."""
        pass
