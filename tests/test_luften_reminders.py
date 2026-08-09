import os
import unittest
from datetime import datetime, timezone

os.environ.setdefault("START_LAT", "0")
os.environ.setdefault("START_LON", "0")
os.environ.setdefault("TIMEZONE", "UTC")
os.environ.setdefault("NTFY_TOPIC", "test-topic")

import planner


class VentilationReminderTests(unittest.TestCase):
    def test_evening_reminder_for_hot_tomorrow(self):
        now = datetime(2026, 8, 9, 20, 0, tzinfo=timezone.utc)
        idx = {
            datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc): (0.0, 0, 31.0),
            datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc): (0.0, 0, 35.0),
            datetime(2026, 8, 10, 16, 0, tzinfo=timezone.utc): (0.0, 0, 27.0),
        }

        reminders = planner.get_luften_reminders(now, idx, {"ventilation_notifications": {}})
        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders[0]["kind"], "evening")
        self.assertIn("tomorrow", reminders[0]["message"].lower())

    def test_cooldown_reminder_when_hot_day_cools_off(self):
        now = datetime(2026, 8, 9, 15, 0, tzinfo=timezone.utc)
        idx = {
            datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc): (0.0, 0, 35.0),
            datetime(2026, 8, 9, 15, 0, tzinfo=timezone.utc): (0.0, 0, 23.0),
            datetime(2026, 8, 9, 18, 0, tzinfo=timezone.utc): (0.0, 0, 23.0),
        }

        reminders = planner.get_luften_reminders(now, idx, {"ventilation_notifications": {}})
        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders[0]["kind"], "cooldown")
        self.assertIn("start Lüften", reminders[0]["message"])


if __name__ == "__main__":
    unittest.main()
