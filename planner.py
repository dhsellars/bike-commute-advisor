import json
import requests
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    class ZoneInfo(tzinfo):
        def __init__(self, key):
            self.key = key
            if key in {"UTC", "Etc/UTC", "Etc/GMT"}:
                self._tz = timezone.utc
            else:
                raise ValueError(f"Unsupported timezone: {key}")

        def utcoffset(self, dt):
            return self._tz.utcoffset(dt)

        def dst(self, dt):
            return self._tz.dst(dt)

        def tzname(self, dt):
            return self._tz.tzname(dt)

        def fromutc(self, dt):
            return dt.replace(tzinfo=self)


def get_timezone(tz_name: str):
    try:
        return ZoneInfo(tz_name)
    except Exception:
        if tz_name in {"UTC", "Etc/UTC", "Etc/GMT"}:
            return timezone.utc
        raise
from config import (
    LAT, LON,
    TIMEZONE, START_HOUR, END_HOUR,
    MAX_RAIN_MM, MAX_POP,
    POP_DELTA_NOTIFY, RAIN_DELTA_NOTIFY, NOTIFY_ON_STATUS_CHANGE,
    NTFY_URL, NTFY_LUFTEN_URL,
    HOT_HIGH_TEMP_F_THRESHOLD, HOT_COOL_TEMP_F_THRESHOLD,
    WEATHER_REPORT_NOTIFY_HOUR, WEATHER_REPORT_START_HOUR, WEATHER_REPORT_END_HOUR,
    STATE_FILE
)

# --------------------------------------------
# State helpers
# --------------------------------------------
def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {"last_notification": None, "last_snapshot": None}

    state.setdefault("ventilation_notifications", {})
    return state

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# --------------------------------------------
# Notify
# --------------------------------------------
def notify(message, ntfy_url=None):
    target_url = ntfy_url or NTFY_URL
    if not target_url:
        return

    try:
        requests.post(target_url, data=message.encode("utf-8"), timeout=10)
    except Exception:
        pass


# --------------------------------------------
# Weather fetch
# --------------------------------------------
def get_weather_localtime():
    base = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "precipitation,precipitation_probability,temperature_2m",
        "forecast_days": 2,
        "timezone": TIMEZONE,
    }
    r = requests.get(base, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


# --------------------------------------------
# Time helpers
# --------------------------------------------
def next_occurrence_of_hour(now_local: datetime, hour: int) -> datetime:
    candidate = now_local.replace(hour=hour, minute=0, second=0, microsecond=0)
    if candidate <= now_local:
        candidate += timedelta(days=1)
    return candidate


def build_local_dt_index(weather_json, tz: str):
    times = weather_json["hourly"]["time"]
    rain = weather_json["hourly"]["precipitation"]
    pop = weather_json["hourly"]["precipitation_probability"]
    temp = weather_json["hourly"]["temperature_2m"]

    z = get_timezone(tz)
    idx = {}
    for t, r_mm, p, t_c in zip(times, rain, pop, temp):
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt_local = dt.replace(tzinfo=z)
        else:
            dt_local = dt.astimezone(z)
        idx[dt_local] = (float(r_mm), int(p), float(t_c))
    return idx


# --------------------------------------------
# Status + snapshot
# --------------------------------------------
def classify(r_mm: float, p: int) -> str:
    if r_mm <= MAX_RAIN_MM and p <= MAX_POP:
        return "🟢 good"
    elif r_mm <= MAX_RAIN_MM * 2 and p <= MAX_POP * 2:
        return "🟡 meh"
    else:
        return "🔴 nope"


def format_status(status: str, word_width: int = 6) -> str:
    parts = status.split(" ", 1)
    if len(parts) == 2:
        emoji, word = parts
    else:
        emoji, word = "", status

    padded_word = word.ljust(word_width)
    return f"{emoji} {padded_word}"


def make_snapshot(now_local: datetime, idx: dict) -> dict:
    hours_map = {}
    tz = get_timezone(TIMEZONE)

    for h in range(START_HOUR, END_HOUR + 1):
        target_dt = next_occurrence_of_hour(now_local, h).astimezone(tz)
        vals = idx.get(target_dt)
        if vals is None:
            continue

        r_mm, p, t_c = vals
        status = classify(r_mm, p)

        hours_map[f"{h:02}"] = {
            "iso": target_dt.strftime("%m.%dT%H:%M"),
            "dow": target_dt.strftime("%a"),
            "r_mm": round(r_mm, 1),
            "pop": int(p),
            "temp_c": round(t_c, 1),
            "status": status,
        }

    return {"hours": hours_map}


def make_commute_summary(now_local: datetime, idx: dict) -> dict:
    tz = get_timezone(TIMEZONE)
    tomorrow = (now_local + timedelta(days=1)).date()
    pleasant_hours = []

    for h in range(START_HOUR, END_HOUR + 1):
        target_dt = next_occurrence_of_hour(now_local, h).astimezone(tz)
        if target_dt.date() != tomorrow:
            continue

        vals = get_hourly_value(idx, target_dt)
        if vals is None:
            continue

        r_mm, p, t_c, sun = vals
        temp_f = (t_c * 9 / 5) + 32
        score = 0
        if p <= 20:
            score += 2
        elif p <= 40:
            score += 1
        if r_mm <= 0.5:
            score += 2
        elif r_mm <= 1.5:
            score += 1
        if sun >= 50:
            score += 2
        elif sun >= 25:
            score += 1
        if 60 <= temp_f <= 80:
            score += 2
        elif 50 <= temp_f <= 90:
            score += 1

        pleasant_hours.append({
            "hour": h,
            "temp_f": round(temp_f, 1),
            "pop": int(p),
            "rain_mm": round(r_mm, 1),
            "sun": int(sun),
            "score": score,
            "pleasant": score >= 4,
        })

    pleasant_count = sum(1 for entry in pleasant_hours if entry["pleasant"])
    best_hour = max(pleasant_hours, key=lambda entry: (entry["pleasant"], entry["score"], -entry["pop"]), default=None)

    if not pleasant_hours:
        overall = "uncertain"
        summary_text = "No commute forecast was available for tomorrow."
    elif pleasant_count >= 3:
        overall = "pleasant"
        summary_text = "Tomorrow looks pleasant for a bike commute."
    elif pleasant_count >= 1:
        overall = "mixed"
        summary_text = "Tomorrow is a mixed bike commute day."
    else:
        overall = "not pleasant"
        summary_text = "Tomorrow looks unpleasant for a bike commute."

    return {
        "target_date": tomorrow,
        "overall": overall,
        "summary": summary_text,
        "pleasant_hours": pleasant_hours,
        "best_hour": best_hour,
    }


def get_commute_notification(now_local: datetime, idx: dict, state: dict) -> Optional[dict]:
    now_local = now_local.astimezone(get_timezone(TIMEZONE)) if now_local.tzinfo else now_local.replace(tzinfo=get_timezone(TIMEZONE))

    if now_local.hour != 20:
        return None

    last_sent = state.get("last_commute_notification_date")
    summary = make_commute_summary(now_local, idx)
    if last_sent == summary["target_date"].isoformat():
        return None

    target_date = summary["target_date"]
    best_hour = summary["best_hour"]
    if not best_hour:
        return None

    if summary["overall"] == "pleasant":
        message = (
            f"Bike commute: {summary['summary']} "
            f"Best window is around {hour_label(best_hour['hour'])} with {best_hour['temp_f']:.0f}°F, "
            f"{best_hour['pop']}% rain chance, and {best_hour['sun']}% sun."
        )
    else:
        message = (
            f"Bike commute: {summary['summary']} "
            f"Best window is around {hour_label(best_hour['hour'])} with {best_hour['temp_f']:.0f}°F, "
            f"{best_hour['pop']}% rain chance, and {best_hour['sun']}% sun."
        )

    return {
        "kind": "commute",
        "message": message,
        "target_date": target_date,
    }


def hour_label(h: int) -> str:
    if h == 0:
        label = "12am"
    elif 1 <= h < 12:
        label = f"{h}am"
    elif h == 12:
        label = "12pm"
    else:
        label = f"{h-12}pm"

    return label.ljust(4)


def collect_daily_temps(idx: dict, target_date) -> list:
    temps = []
    for dt, values in idx.items():
        if dt.date() != target_date:
            continue
        if START_HOUR <= dt.hour <= END_HOUR:
            temps.append((values[2] * 9 / 5) + 32)
    return temps


def get_hourly_value(idx: dict, dt: datetime):
    if dt in idx:
        return idx[dt]

    for candidate_dt, values in idx.items():
        if (
            candidate_dt.year == dt.year
            and candidate_dt.month == dt.month
            and candidate_dt.day == dt.day
            and candidate_dt.hour == dt.hour
        ):
            return values

    return None


def build_weather_report_lines(now_local: datetime, idx: dict) -> list:
    tz = get_timezone(TIMEZONE)
    tomorrow = (now_local + timedelta(days=1)).date()
    lines = []

    for hour in range(WEATHER_REPORT_START_HOUR, WEATHER_REPORT_END_HOUR + 1):
        target_dt = next_occurrence_of_hour(now_local, hour).astimezone(tz)
        if target_dt.date() != tomorrow:
            continue

        vals = get_hourly_value(idx, target_dt)
        if vals is None:
            continue

        r_mm, p, t_c = vals[:3]
        temp_f = (t_c * 9 / 5) + 32
        lines.append(f"{hour_label(hour)} {int(p)}% rain, {temp_f:.0f}°F")

    return lines


def get_evening_weather_report(now_local: datetime, idx: dict, state: dict) -> Optional[dict]:
    now_local = now_local.astimezone(get_timezone(TIMEZONE)) if now_local.tzinfo else now_local.replace(tzinfo=get_timezone(TIMEZONE))

    if now_local.hour != WEATHER_REPORT_NOTIFY_HOUR:
        return None

    last_sent = state.get("last_evening_weather_date")
    tomorrow = now_local.date() + timedelta(days=1)
    if last_sent == tomorrow.isoformat():
        return None

    hourly_lines = build_weather_report_lines(now_local, idx)
    if not hourly_lines:
        return None

    tomorrow_temps = collect_daily_temps(idx, tomorrow)
    high_temp_f = max(tomorrow_temps) if tomorrow_temps else None
    summary = "; ".join(hourly_lines)
    message = (
        f"Tomorrow's weather from {hour_label(WEATHER_REPORT_START_HOUR)} to {hour_label(WEATHER_REPORT_END_HOUR)}: {summary}."
    )
    if high_temp_f is not None and high_temp_f > HOT_HIGH_TEMP_F_THRESHOLD:
        message += (
            f" Tomorrow's high is expected to reach {high_temp_f:.0f}°F, so cool down the house as much as possible tomorrow."
        )

    return {
        "kind": "weather_report",
        "message": message,
        "target_date": tomorrow,
    }


def get_luften_reminders(now_local: datetime, idx: dict, state: dict) -> list:
    reminders = []
    notifications = state.get("ventilation_notifications", {}) or {}
    now_local = now_local.astimezone(get_timezone(TIMEZONE)) if now_local.tzinfo else now_local.replace(tzinfo=get_timezone(TIMEZONE))

    current_hour_dt = now_local.replace(minute=0, second=0, microsecond=0)

    if now_local.hour == WEATHER_REPORT_NOTIFY_HOUR:
        tomorrow = now_local.date() + timedelta(days=1)
        tomorrow_temps = collect_daily_temps(idx, tomorrow)
        if tomorrow_temps and max(tomorrow_temps) > HOT_HIGH_TEMP_F_THRESHOLD:
            evening_key = f"evening:{tomorrow.isoformat()}"
            if not notifications.get(evening_key):
                reminders.append({
                    "kind": "evening",
                    "key": evening_key,
                    "message": (
                        f"Lüften reminder: tomorrow is expected to hit {max(tomorrow_temps):.0f}°F, "
                        "so open the windows tonight at 8pm and capture the cool air for the morning."
                    ),
                })

    if START_HOUR <= now_local.hour <= END_HOUR:
        current_vals = get_hourly_value(idx, current_hour_dt)
        if current_vals is not None:
            current_temp_f = (current_vals[2] * 9 / 5) + 32
            today_temps = collect_daily_temps(idx, now_local.date())
            if (
                today_temps
                and max(today_temps) > HOT_HIGH_TEMP_F_THRESHOLD
                and current_temp_f < HOT_COOL_TEMP_F_THRESHOLD
            ):
                cooldown_key = f"cooldown:{now_local.date().isoformat()}"
                if not notifications.get(cooldown_key):
                    reminders.append({
                        "kind": "cooldown",
                        "key": cooldown_key,
                        "message": (
                            f"Lüften reminder: it has cooled down to {current_temp_f:.0f}°F today "
                            "after a hotter spell, so start Lüften again now."
                        ),
                    })

    return reminders


# --------------------------------------------
# Main
# --------------------------------------------
def main():
    state = load_state()
    now_local = datetime.now(get_timezone(TIMEZONE))

    weather = get_weather_localtime()
    dt_index = build_local_dt_index(weather, TIMEZONE)

    should_save = False
    commute_notification = get_commute_notification(now_local, dt_index, state)
    if commute_notification:
        notify(commute_notification["message"], ntfy_url=NTFY_URL)
        state["last_notification"] = commute_notification["message"]
        state["last_commute_notification_date"] = commute_notification["target_date"].isoformat()
        should_save = True

    evening_report = get_evening_weather_report(now_local, dt_index, state)
    if evening_report:
        notify(evening_report["message"], ntfy_url=NTFY_URL)
        state["last_evening_weather_date"] = evening_report["target_date"].isoformat()
        should_save = True

    reminders = get_luften_reminders(now_local, dt_index, state)
    for reminder in reminders:
        notify(reminder["message"], ntfy_url=NTFY_LUFTEN_URL)
        state.setdefault("ventilation_notifications", {})[reminder["key"]] = True
        should_save = True

    if should_save:
        save_state(state)


if __name__ == "__main__":
    main()
