import uuid
from datetime import datetime, timezone
import pytest

from app.models.compliance_enums import NotificationSeverity, NotificationType
from app.models.notification import Notification
from app.services.notification_service import (
    CompositeNotificationProvider,
    InAppNotificationProvider,
    LoggingNotificationProvider,
    NoopNotificationProvider,
    NotificationService,
    get_notification_provider,
)


def _sample_notification() -> Notification:
    return Notification(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        type=NotificationType.TASK_OVERDUE,
        title="Test Notification",
        message="This is a test notification message",
        severity=NotificationSeverity.WARNING,
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )


class MockTrackingProvider:
    def __init__(self, should_fail: bool = False):
        self.sent: list[Notification] = []
        self.should_fail = should_fail

    async def send(self, notification: Notification) -> None:
        if self.should_fail:
            raise RuntimeError("Provider delivery simulated failure")
        self.sent.append(notification)


@pytest.mark.asyncio
class TestNotificationProviders:
    async def test_in_app_provider(self):
        provider = InAppNotificationProvider()
        notif = _sample_notification()
        res = await provider.send(notif)
        assert res is None

    async def test_logging_provider(self, caplog):
        import logging
        caplog.set_level(logging.INFO)
        provider = LoggingNotificationProvider()
        notif = _sample_notification()
        await provider.send(notif)
        assert "Test Notification" in caplog.text

    async def test_noop_provider(self):
        provider = NoopNotificationProvider()
        notif = _sample_notification()
        res = await provider.send(notif)
        assert res is None

    async def test_composite_provider_dispatches_to_all(self):
        p1 = MockTrackingProvider()
        p2 = MockTrackingProvider()
        composite = CompositeNotificationProvider([p1, p2])
        notif = _sample_notification()
        await composite.send(notif)
        assert len(p1.sent) == 1
        assert len(p2.sent) == 1
        assert p1.sent[0] == notif
        assert p2.sent[0] == notif

    async def test_composite_provider_fault_tolerance(self, caplog):
        p_failing = MockTrackingProvider(should_fail=True)
        p_working = MockTrackingProvider(should_fail=False)
        composite = CompositeNotificationProvider([p_failing, p_working])
        notif = _sample_notification()
        # Should not raise exception
        await composite.send(notif)
        # Working provider still received notification
        assert len(p_working.sent) == 1
        assert "Provider delivery simulated failure" in caplog.text

    async def test_factory_function(self):
        assert isinstance(get_notification_provider("in_app"), InAppNotificationProvider)
        assert isinstance(get_notification_provider("logging"), LoggingNotificationProvider)
        assert isinstance(get_notification_provider("noop"), NoopNotificationProvider)
        assert isinstance(get_notification_provider("composite"), CompositeNotificationProvider)
        assert isinstance(get_notification_provider("unknown_type"), InAppNotificationProvider)

    async def test_service_with_custom_provider(self, db_session, company_a_with_admin):
        company, admin = company_a_with_admin
        mock_p = MockTrackingProvider()
        service = NotificationService(db_session, provider=mock_p)

        created = await service.notify(
            company_id=company.id,
            user_id=admin.id,
            notification_type=NotificationType.TASK_ASSIGNED,
            title="Custom Provider Test",
            message="Testing custom provider dispatch",
        )
        assert created is not None
        assert len(mock_p.sent) == 1
        assert mock_p.sent[0].title == "Custom Provider Test"
