import os

# Secrets (in GitHub Actions)
LAT = float(os.environ["START_LAT"])
LON = float(os.environ["START_LON"])

TIMEZONE = os.environ["TIMEZONE"]

NTFY_TOPIC = os.environ["NTFY_TOPIC"]
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

NTFY_LUFTEN_TOPIC = os.environ.get("NTFY_LUFTEN_TOPIC", NTFY_TOPIC)
NTFY_LUFTEN_URL = f"https://ntfy.sh/{NTFY_LUFTEN_TOPIC}" if NTFY_LUFTEN_TOPIC else None

# Public config (safe to commit)
START_HOUR = 7
END_HOUR = 20

MAX_RAIN_MM = 0.5
MAX_POP = 40


# Notification tuning
POP_DELTA_NOTIFY = 5          # percentage points
RAIN_DELTA_NOTIFY = 0.5       # mm
NOTIFY_ON_STATUS_CHANGE = True

LUFTEN_HIGH_TEMP_F_THRESHOLD = 90.0
LUFTEN_COOL_TEMP_F_THRESHOLD = 75.0
LUFTEN_EVENING_NOTIFY_HOUR = 20

STATE_FILE = f"state_{NTFY_TOPIC}.json"
