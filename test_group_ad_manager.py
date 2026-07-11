#!/usr/bin/env python3
"""
Focused tests for GroupAdManager scheduling and controls.
"""

import os
import sys
import time
import unittest
import inspect
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

from signalbot.core.group_ad_manager import GroupAdManager
from signalbot.core.signal_handler import SignalHandler


class _FakeSignalHandler:
    def __init__(self):
        self.sent = []

    def send_message(self, recipient, message, attachments=None):
        self.sent.append((recipient, message))
        return True


class GroupAdManagerTests(unittest.TestCase):
    def setUp(self):
        self.signal_handler = _FakeSignalHandler()
        self.manager = GroupAdManager(self.signal_handler, poll_interval_seconds=1)

    def tearDown(self):
        self.manager.stop()

    def test_add_update_enable_disable_remove_and_manual_post(self):
        self.manager.add_group("g1", "Group One", 2)
        self.assertTrue(self.manager.update_group_frequency("g1", 3))
        self.assertTrue(self.manager.disable_group("g1"))
        self.assertTrue(self.manager.enable_group("g1"))
        self.assertTrue(self.manager.post_ad_now("g1"))
        self.assertEqual(self.signal_handler.sent[-1][0], "g1")
        status = self.manager.get_status()
        self.assertEqual(status["group_count"], 1)
        self.assertEqual(status["groups"][0]["ads_per_day"], 3)
        self.assertTrue(self.manager.remove_group("g1"))
        self.assertFalse(self.manager.remove_group("g1"))

    def test_scheduler_posts_due_groups_without_spam(self):
        self.manager.add_group("g2", "Group Two", 24)
        self.manager.start()
        time.sleep(1.2)
        first_count = len(self.signal_handler.sent)
        self.assertGreaterEqual(first_count, 1)

        time.sleep(0.3)
        self.assertEqual(len(self.signal_handler.sent), first_count)

        with self.manager._lock:
            self.manager._groups["g2"]["last_post_at"] = datetime.now(timezone.utc) - timedelta(hours=2)
        time.sleep(1.2)
        self.assertGreater(len(self.signal_handler.sent), first_count)

    def test_signal_handler_exposes_join_and_leave_group_methods(self):
        source = inspect.getsource(SignalHandler)
        self.assertIn("def join_group", source)
        self.assertIn("joinGroup", source)
        self.assertIn("def leave_group", source)
        self.assertIn("quitGroup", source)


if __name__ == "__main__":
    unittest.main()
