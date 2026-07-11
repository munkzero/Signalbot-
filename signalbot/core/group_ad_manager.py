"""
Group advertisement scheduler for Signal groups.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional


class GroupAdManager:
    """Manage per-group advertisement scheduling and posting."""

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
                "enabled": True,
                "last_post_at": last_post_at,
            }

    def remove_group(self, group_id):
        with self._lock:
            return self._groups.pop(group_id, None) is not None

    def update_group_frequency(self, group_id, ads_per_day):
        frequency = self._validate_ads_per_day(ads_per_day)
        with self._lock:
            group = self._groups.get(group_id)
            if not group:
                return False
            group["ads_per_day"] = frequency
            return True

    def enable_group(self, group_id):
        with self._lock:
            group = self._groups.get(group_id)
            if not group:
                return False
            group["enabled"] = True
            return True

    def disable_group(self, group_id):
        with self._lock:
            group = self._groups.get(group_id)
            if not group:
                return False
            group["enabled"] = False
            return True

    def post_ad_now(self, group_id):
        with self._lock:
            group = self._groups.get(group_id)
            if not group:
                return False
        return self._post_to_group(group_id)

    def set_ad_message(self, message):
        cleaned = (message or "").strip()
        if not cleaned:
            raise ValueError("Ad message cannot be empty")
        with self._lock:
            self._ad_message = cleaned

    def start(self):
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_scheduler, daemon=True, name="GroupAdManager")
            self._thread.start()
            self._running = True

    def stop(self):
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
        except Exception:
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
        interval_seconds = 86400 / group["ads_per_day"]
        elapsed_seconds = max(0.0, (now - last_post_at).total_seconds())
        return elapsed_seconds >= interval_seconds

    @staticmethod
    def _validate_ads_per_day(ads_per_day):
        value = int(ads_per_day)
        if value < 1 or value > 24:
            raise ValueError("ads_per_day must be between 1 and 24")
        return value
