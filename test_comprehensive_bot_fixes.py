#!/usr/bin/env python3
"""
Targeted verification for comprehensive reliability and cleanup fixes.
"""

from pathlib import Path


ROOT = Path(__file__).parent


def read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text()


def assert_contains(content: str, needle: str, label: str) -> None:
    if needle not in content:
        raise AssertionError(f"Missing {label}: {needle}")


def test_signal_handler_health_and_cleanup():
    content = read("signalbot/core/signal_handler.py")
    checks = [
        ("self._status =", "status tracking"),
        ("def _run_signal_cli(", "signal-cli helper"),
        ("def get_health_status(", "health status accessor"),
        ("def clear_all_live_conversations(", "live cache cleanup"),
    ]
    for needle, label in checks:
        assert_contains(content, needle, label)


def test_wallet_retry_and_health():
    content = read("signalbot/core/monero_wallet.py")
    checks = [
        ("wallet_password is None", "empty-string password support"),
        ("def _rpc_ping(", "raw RPC ping helper"),
        ("def set_backup_rpc_endpoints(", "backup endpoint support"),
        ("def get_health_status(", "wallet health status"),
    ]
    for needle, label in checks:
        assert_contains(content, needle, label)


def test_payment_retry_queue():
    content = read("signalbot/core/payments.py")
    checks = [
        ("self.failed_payment_checks = deque()", "retry queue"),
        ("def _queue_failed_payment_check(", "failed check queue helper"),
        ("def _retry_failed_payment_checks(", "retry worker"),
        ("def get_health_status(", "payment health status"),
    ]
    for needle, label in checks:
        assert_contains(content, needle, label)


def test_cleanup_schema_and_manager():
    db_content = read("signalbot/database/db.py")
    manager_content = read("signalbot/core/cleanup_manager.py")
    order_content = read("signalbot/models/order.py")
    message_content = read("signalbot/models/message.py")

    db_checks = [
        ("class MessageArchive(Base):", "message archive table"),
        ("class OrderArchive(Base):", "order archive table"),
        ("message_retention_days = Column(Integer, default=30)", "seller retention column"),
        ("archived_at = Column(DateTime, nullable=True)", "archive timestamp column"),
    ]
    for needle, label in db_checks:
        assert_contains(db_content, needle, label)

    manager_checks = [
        ("class CleanupManager:", "cleanup manager"),
        ("def run_scheduled_cleanup(", "scheduled cleanup"),
        ("def run_full_cleanup(", "full cleanup"),
        ("def get_storage_usage(", "storage usage"),
    ]
    for needle, label in manager_checks:
        assert_contains(manager_content, needle, label)

    order_checks = [
        ("def archive_orders_older_than(", "order archival"),
        ("def purge_archived_orders(", "order archive purge"),
        ("def delete_all_orders_and_archives(", "order full cleanup"),
    ]
    for needle, label in order_checks:
        assert_contains(order_content, needle, label)

    message_checks = [
        ("def archive_messages_older_than(", "message archival"),
        ("def purge_archived_messages(", "message archive purge"),
        ("def delete_all_messages(", "message full cleanup"),
    ]
    for needle, label in message_checks:
        assert_contains(message_content, needle, label)


def test_dashboard_status_and_live_conversations():
    content = read("signalbot/gui/dashboard.py")
    checks = [
        ("Load conversation list from live Signal conversations only.", "live conversation-only messaging"),
        ("self.signal_health_label = QLabel(", "signal status label"),
        ("self.storage_usage_label = QLabel(", "storage usage label"),
        ("def run_cleanup_now(", "manual cleanup UI"),
        ("self.cleanup_manager = CleanupManager(", "dashboard cleanup manager"),
    ]
    for needle, label in checks:
        assert_contains(content, needle, label)


def main():
    tests = [
        test_signal_handler_health_and_cleanup,
        test_wallet_retry_and_health,
        test_payment_retry_queue,
        test_cleanup_schema_and_manager,
        test_dashboard_status_and_live_conversations,
    ]
    failures = []
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
        except Exception as exc:
            print(f"FAIL: {test.__name__}: {exc}")
            failures.append(test.__name__)

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
