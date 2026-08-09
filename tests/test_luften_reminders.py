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

    def test_commute_notification_is_created_for_pleasant_tomorrow(self):
        now = datetime(2026, 8, 9, 20, 0, tzinfo=timezone.utc)
        idx = {
            datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc): (0.0, 5, 21.0, 20.0),
            datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc): (0.0, 10, 22.0, 25.0),
            datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc): (0.0, 15, 23.0, 30.0),
        }

        notification = planner.get_commute_notification(now, idx, {"last_commute_notification_date": None})
        self.assertIsNotNone(notification)
        self.assertIn("pleasant", notification["message"].lower())
        self.assertEqual(notification["target_date"], datetime(2026, 8, 10, 0, 0).date())

    def test_commute_notification_is_skipped_if_already_sent_today(self):
        now = datetime(2026, 8, 9, 20, 0, tzinfo=timezone.utc)
        idx = {
            datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc): (0.0, 5, 21.0, 20.0),
        }

        notification = planner.get_commute_notification(now, idx, {"last_commute_notification_date": "2026-08-10"})
        self.assertIsNone(notification)

    def test_evening_weather_report_includes_hourly_summary_for_tomorrow(self):
        now = datetime(2026, 8, 9, 20, 0, tzinfo=timezone.utc)
        idx = {
            datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc): (0.1, 10, 24.0),
            datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc): (0.0, 5, 27.0),
            datetime(2026, 8, 10, 17, 0, tzinfo=timezone.utc): (0.0, 0, 31.0),
        }

        notification = planner.get_evening_weather_report(now, idx, {"last_evening_weather_date": None})
        self.assertIsNotNone(notification)
        self.assertIn("tomorrow", notification["message"].lower())
        self.assertIn("8am", notification["message"])
        self.assertIn("5pm", notification["message"])
        self.assertIn("10%", notification["message"])

    def test_hot_tomorrow_uses_cooling_message(self):
        now = datetime(2026, 8, 9, 20, 0, tzinfo=timezone.utc)
        idx = {
            datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc): (0.0, 0, 31.0),
            datetime(2026, 8, 10, 16, 0, tzinfo=timezone.utc): (0.0, 0, 32.0),
        }

        notification = planner.get_evening_weather_report(now, idx, {"last_evening_weather_date": None})
        self.assertIsNotNone(notification)
        self.assertIn("cool down the house", notification["message"].lower())

    def test_commute_summary_handles_three_value_hourly_weather_tuples(self):
        now = datetime(2026, 8, 9, 20, 0, tzinfo=timezone.utc)
        idx = {
            datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc): (0.1, 10, 21.0),
            datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc): (0.0, 5, 22.0),
            datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc): (0.0, 0, 23.0),
        }

        summary = planner.make_commute_summary(now, idx)
        self.assertEqual(summary["target_date"], datetime(2026, 8, 10, 0, 0).date())
        self.assertIn("overall", summary)
        self.assertIsNotNone(summary["best_hour"])


if __name__ == "__main__":
    unittest.main()
