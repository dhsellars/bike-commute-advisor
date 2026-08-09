# 🚴‍♂️ Bike Commute Weather Planner  
A lightweight, automated tool that checks hourly weather forecasts and sends push notifications with the best rain‑free times to travel.

This project runs entirely in **GitHub Actions** (free), requires **no servers**, and sends notifications via **ntfy** directly to your phone.

It’s designed for commuters who want a simple, reliable way to know:

- When the next dry travel window is  
- How the day’s dry hours look at 7am  
- Whether conditions change during the day  
- What the temperature will be (in °F) at each dry hour  

The tool is intentionally quiet — it only notifies you when something meaningful changes.

---

## 🌤️ What the application does

Every weekday (Monday–Friday):

### **At 7:00 AM**
- Fetches the hourly weather forecast for the day  
- Identifies all **rain‑free hours** between **7:00 AM and 7:00 PM**  
- Sends a **daily summary** push notification with:
  - Each dry hour  
  - The temperature in °F at that hour  

### **Every hour between 7:00 AM and 5:00 PM**
- Re-checks the weather  
- Compares the new dry hours to the last notification  
- Sends an **update notification only if**:
  - The set of dry hours has changed  
  - (Temperature changes alone do *not* trigger updates)

### **At 8:00 PM**
- If tomorrow’s forecast is expected to exceed 90°F, a separate Lüften reminder is sent to the ventilation feed to suggest opening the windows and capturing the cool air for morning.

### **During the day after a hot spell**
- If the day’s high was above 90°F and the temperature later drops below 75°F, another Lüften reminder is sent to prompt you to start ventilating again.

### **After 5:00 PM**
- No more commute notifications for the day  

### **State tracking**
The tool stores the last-notified dry hours in a small `state.json` file committed to the repository.  
This allows GitHub Actions to remember what it told you last time.

---

## 📱 Push notifications via ntfy

This project uses **ntfy** for free, instant push notifications.

To subscribe:

1. Install the ntfy app (iOS or Android)  
2. Add a subscription  
3. Enter **only the topic name**, for example:  
   ```
   bike-commute-d-48_68-9_01
   ```
4. Save  

You’ll now receive notifications automatically.

---

## 📁 Repository structure

```
bike-commute/
  ├── planner.py        # main logic
  ├── config.py         # user configuration
  ├── state.json        # last-notified state (auto-updated)
  └── .github/
      └── workflows/
          └── run.yml   # GitHub Actions scheduler
```

---
🧑‍💻 Using this project for your own commute
- Clone the repository
- Copy .env.example → .env
- Fill in your location, commute hours, and ntfy topic
- Subscribe to your ntfy topic in the app
- Enable GitHub Actions in your fork
- Done


## ⚙️ Configuration (adapt for your location & needs)

All user‑editable settings live in **config.py**.

Here’s what you can change:

### **1. Location**
Update latitude, longitude, and timezone:

```python
LAT = 48.68
LON = 9.01
TIMEZONE = "Europe/Berlin"
```

To find your coordinates:  
Search “your city latitude longitude” online.

---

### **2. Commute window**
Define the hours during which you might travel:

```python
START_HOUR = 7
END_HOUR   = 19
```

Example:  
If you only travel in the morning:

```python
START_HOUR = 6
END_HOUR   = 10
```

---

### **3. Notification cutoff**
Stop sending updates after a certain hour:

```python
NOTIFY_END_HOUR = 17
```

---

### **4. Rain tolerance**
Control what counts as “dry”:

```python
MAX_RAIN_MM = 0.0      # 0.0 = absolutely no rain
MAX_POP = 20           # precipitation probability threshold (%)
```

If you’re okay with a tiny drizzle:

```python
MAX_RAIN_MM = 0.1
```

---

### **5. Push notification topics**
Choose any topic name you like for commuting alerts and an optional second topic for Lüften reminders:

```python
NTFY_TOPIC = "bike-commute-d-48_68-9_01"
NTFY_LUFTEN_TOPIC = "bike-commute-luften"
```

If you change them, update your ntfy app subscriptions too.

---

## 🕒 Scheduling (GitHub Actions)

The workflow runs:

- **Every hour** on weekdays  
- **Always at 7am** for the daily summary  

You can adjust the schedule in `.github/workflows/run.yml`:

```yaml
schedule:
  - cron: "0 * * * 1-5"   # every hour, Monday–Friday
```

Examples:

- Every 30 minutes: `*/30 * * * 1-5`
- Only mornings: `0 7-12 * * 1-5`

---

## 🧪 Testing

You can manually trigger a run:

1. Go to your GitHub repo  
2. Click **Actions**  
3. Select **Bike Commute Planner**  
4. Click **Run workflow**

You should receive a push notification within seconds.

---

## 🧰 Requirements

- GitHub account  
- ntfy app (optional but recommended)  
- No servers, no hosting, no API keys  

Everything runs inside GitHub’s free tier.

---
