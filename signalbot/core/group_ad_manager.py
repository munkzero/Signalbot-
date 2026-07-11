"""
Group advertisement scheduler for Signal groups.
"""

from __future__ import annotations

import threading
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GroupAdManager:
    """Manage per-group advertisement scheduling and posting."""

    SECONDS_PER_DAY = 86400
    DEFAULT_AD_MESSAGE = (
        "👋 Hey! I'm a 24/7 shopping bot\n\n"
        "📦 To browse my catalog: DM me\n"
        "💬 Send: \"catalog\" or \"help\"\n\n"
        "🔎 To check order status: DM \"status #ORDER_ID\""
    )

    def __init__(self, signal_handler, poll_interval_seconds: int = 30):
        self.signal_handler = signal_handler
        self.poll_interval_seconds = max(1, int(poll_interval_seconds))
        self._groups: Dict[str, Dict] = {}
        self._ad_message = self.DEFAULT_AD_MESSAGE
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def add_group(self, group_id, name, ads_per_day):
        """Add or update a managed group with posting frequency."""
        group_id = (group_id or "").strip()
        if not group_id:
            raise ValueError("group_id is required")
        frequency = self._validate_ads_per_day(ads_per_day)
        with self._lock:
            existing = self._groups.get(group_id)
            last_post_at = existing.get("last_post_at") if existing else None
            self._groups[group_id] = {
                "group_id": group_id,
                "name": name or "Unknown Group",
                "ads_per_day": frequency,
                "interval_seconds": self.SECONDS_PER_DAY / frequency,
                "enabled": True,
                "last_post_at": last_post_at,
            }

    def remove_group(self, group_id):
        """Remove a group from ad management."""
        with self._lock:
            return self._groups.pop(group_id, None) is not None

    def update_group_frequency(self, group_id, ads_per_day):
        """Update how many ads per day are allowed for a group."""
        frequency = self._validate_ads_per_day(ads_per_day)
        with self._lock:
            group = self._groups.get(group_id)
            if not group:
                return False
            group["ads_per_day"] = frequency
            group["interval_seconds"] = self.SECONDS_PER_DAY / frequency
            return True

    def enable_group(self, group_id):
        """Enable scheduled ad posting for a group."""
        with self._lock:
            group = self._groups.get(group_id)
            if not group:
                return False
            group["enabled"] = True
            return True

    def disable_group(self, group_id):
        """Disable scheduled ad posting for a group."""
        with self._lock:
            group = self._groups.get(group_id)
            if not group:
                return False
            group["enabled"] = False
            return True

    def post_ad_now(self, group_id):
        """Immediately post the configured advertisement to a group."""
        with self._lock:
            group = self._groups.get(group_id)
            if not group:
                return False
        return self._post_to_group(group_id)

    def set_ad_message(self, message):
        """Set the shared advertisement message used for all groups."""
        cleaned = (message or "").strip()
        if not cleaned:
            raise ValueError("Ad message cannot be empty")
        with self._lock:
            self._ad_message = cleaned

    def start(self):
        """Start the background scheduler thread."""
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_scheduler, daemon=True, name="GroupAdManager")
            self._thread.start()
            self._running = True

    def stop(self):
        """Stop the background scheduler thread."""
        with self._lock:
            if not self._running:
                return
            self._stop_event.set()
            thread = self._thread
            self._thread = None
            self._running = False
        if thread:
            thread.join(timeout=2)

    def get_status(self):
        """Return scheduler state and managed group metadata."""
        with self._lock:
            groups: List[Dict] = []
            for group in self._groups.values():
                groups.append(
                    {
                        "group_id": group["group_id"],
                        "name": group["name"],
                        "ads_per_day": group["ads_per_day"],
                        "enabled": group["enabled"],
                        "last_post_at": group["last_post_at"].isoformat() if group["last_post_at"] else None,
                    }
                )
            groups.sort(key=lambda g: g["name"].lower())
            enabled_count = sum(1 for group in groups if group["enabled"])
            return {
                "running": self._running,
                "ad_message": self._ad_message,
                "group_count": len(groups),
                "enabled_count": enabled_count,
                "groups": groups,
            }

    def _set_group_last_post_at(self, group_id: str, last_post_at: datetime):
        """Set a group's last-post timestamp."""
        with self._lock:
            group = self._groups.get(group_id)
            if not group:
                return False
            group["last_post_at"] = last_post_at
            return True

    def _run_scheduler(self):
        while not self._stop_event.wait(self.poll_interval_seconds):
            group_ids_to_post = []
            now = datetime.now(timezone.utc)
            with self._lock:
                for group_id, group in self._groups.items():
                    if not group["enabled"]:
                        continue
                    if self._is_due(group, now):
                        group_ids_to_post.append(group_id)
            for group_id in group_ids_to_post:
                self._post_to_group(group_id)

    def _post_to_group(self, group_id):
        with self._lock:
            group = self._groups.get(group_id)
            if not group:
                return False
            message = self._ad_message
        try:
            success = bool(self.signal_handler.send_message(group_id, message))
        except Exception as exc:
            logger.warning("Failed to post group advertisement to %s: %s", group_id, exc)
            success = False
        if success:
            with self._lock:
                if group_id in self._groups:
                    self._groups[group_id]["last_post_at"] = datetime.now(timezone.utc)
        return success

    def _is_due(self, group, now):
        last_post_at = group.get("last_post_at")
        if last_post_at is None:
            return True
        interval_seconds = group.get("interval_seconds", self.SECONDS_PER_DAY / group["ads_per_day"])
        elapsed_seconds = max(0.0, (now - last_post_at).total_seconds())
        return elapsed_seconds >= interval_seconds

    @staticmethod
    def _validate_ads_per_day(ads_per_day):
        value = int(ads_per_day)
        if value < 1 or value > 24:
            raise ValueError("ads_per_day must be between 1 and 24")
        return value
