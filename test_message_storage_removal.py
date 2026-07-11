#!/usr/bin/env python3
"""
Static checks for message-storage removal and live Signal loading.
"""

from pathlib import Path


def main():
    dashboard = (Path(__file__).parent / "signalbot" / "gui" / "dashboard.py").read_text()
    signal_handler = (Path(__file__).parent / "signalbot" / "core" / "signal_handler.py").read_text()

    checks = {
        "No message_manager.add_message calls in dashboard": "message_manager.add_message(" not in dashboard,
        "LoadConversationsWorker removed": "class LoadConversationsWorker" not in dashboard,
        "LoadConversationWorker removed": "class LoadConversationWorker" not in dashboard,
        "Messages tab reads live conversations": "get_live_conversations(" in dashboard,
        "Messages tab reads live conversation messages": "get_live_conversation(" in dashboard,
        "Signal handler has live conversation cache": "def get_live_conversations(" in signal_handler,
        "Signal handler provides list_contacts": "def list_contacts(" in signal_handler,
        "Orders tab includes Delivery Address column": '"Delivery Address"' in dashboard,
    }

    failures = [name for name, ok in checks.items() if not ok]
    for name, ok in checks.items():
        print(f"{'✓' if ok else '✗'} {name}")

    if failures:
        print("\nFailed checks:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("\nAll static checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
