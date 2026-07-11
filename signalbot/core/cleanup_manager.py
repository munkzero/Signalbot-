"""
Scheduled data-retention cleanup for messages and orders.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Dict, Optional

from ..database.db import Order as OrderModel, OrderArchive as OrderArchiveModel
from ..models.message import MessageManager
from ..models.order import OrderManager
from ..models.seller import SellerManager


logger = logging.getLogger(__name__)


class CleanupManager:
    """Runs nightly retention cleanup and manual wipe operations."""

    def __init__(
        self,
        seller_manager: SellerManager,
        message_manager: MessageManager,
        order_manager: OrderManager,
        check_interval_seconds: int = 300
    ):
        self.seller_manager = seller_manager
        self.message_manager = message_manager
        self.order_manager = order_manager
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._status: Dict[str, Optional[object]] = {
            'running': False,
            'last_run_at': None,
            'last_result': 'Not run yet',
            'last_error': None,
        }

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._status['running'] = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="cleanup-manager")
        self._thread.start()
        logger.info("Started cleanup manager")

    def stop(self) -> None:
        self._running = False
        self._status['running'] = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _loop(self) -> None:
        while self._running:
            try:
                if self._should_run_cleanup():
                    self.run_scheduled_cleanup()
            except Exception as exc:
                logger.error("Cleanup manager loop failed: %s", exc)
                self._status['last_error'] = str(exc)
            time.sleep(self.check_interval_seconds)

    def _should_run_cleanup(self) -> bool:
        seller = self.seller_manager.get_seller(1)
        if not seller:
            return False
        last_cleanup_at = seller.last_cleanup_at
        return not last_cleanup_at or last_cleanup_at.date() < datetime.utcnow().date()

    def run_scheduled_cleanup(self) -> Dict[str, int]:
        seller = self.seller_manager.get_seller(1)
        if not seller:
            raise ValueError("Seller configuration not found")

        archived_messages = self.message_manager.archive_messages_older_than(
            seller.message_retention_days,
            seller.archive_retention_days,
        )
        archived_orders = self.order_manager.archive_orders_older_than(
            seller.order_archive_days,
            seller.archive_retention_days,
        )
        purged_messages = self.message_manager.purge_archived_messages(seller.archive_retention_days)
        purged_orders = self.order_manager.purge_archived_orders(seller.archive_retention_days)

        result = {
            'archived_messages': archived_messages,
            'archived_orders': archived_orders,
            'purged_messages': purged_messages,
            'purged_orders': purged_orders,
        }

        seller.last_cleanup_at = datetime.utcnow()
        seller.cleanup_status = (
            f"Archived {archived_messages} message(s), {archived_orders} order(s); "
            f"purged {purged_messages} archived message(s), {purged_orders} archived order(s)"
        )
        self.seller_manager.update_seller(seller)

        self._status['last_run_at'] = seller.last_cleanup_at
        self._status['last_result'] = seller.cleanup_status
        self._status['last_error'] = None
        logger.info("Nightly cleanup complete: %s", seller.cleanup_status)
        return result

    def run_full_cleanup(self) -> Dict[str, int]:
        message_result = self.message_manager.delete_all_messages()
        order_result = self.order_manager.delete_all_orders_and_archives()

        seller = self.seller_manager.get_seller(1)
        if seller:
            seller.last_cleanup_at = datetime.utcnow()
            seller.cleanup_status = "Full cleanup completed"
            self.seller_manager.update_seller(seller)
            self._status['last_run_at'] = seller.last_cleanup_at

        result = {
            **message_result,
            **order_result,
        }
        self._status['last_result'] = f"Full cleanup deleted {sum(result.values())} record(s)"
        self._status['last_error'] = None
        logger.warning("Full cleanup completed: %s", result)
        return result

    def get_status(self) -> Dict[str, Optional[object]]:
        return dict(self._status)

    def get_storage_usage(self) -> Dict[str, int]:
        message_usage = self.message_manager.get_storage_usage()
        return {
            **message_usage,
            'live_orders': self.order_manager.db.session.query(OrderModel).count(),
            'archived_orders': self.order_manager.db.session.query(OrderArchiveModel).count(),
        }
