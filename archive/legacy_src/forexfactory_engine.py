"""
Forex Factory Real-Time Economic Calendar Engine for Trajedor
Fetches and filters live high-impact news events (USD / Gold drivers)
and manages the "Blackout Guard" (halting trades during high volatility spikes).
"""

import json
import urllib.request
from datetime import datetime, timezone


class ForexFactoryEngine:
    CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    CACHE_FILE = "ff_calendar_cache.json"
    CACHE_DURATION_HOURS = 2

    def __init__(self, target_currencies=None, min_impact="High"):
        """
        :param target_currencies: List of currencies to monitor (default: USD, EUR, GBP)
        :param min_impact: 'High', 'Medium', or 'Low'
        """
        self.target_currencies = target_currencies or ["USD", "EUR"]
        self.min_impact = min_impact
        self.events = []

    def fetch_calendar(self, force_refresh=False):
        """Fetch weekly calendar with intelligent local caching."""
        import os, time
        # Check if local cache exists and is fresh
        if not force_refresh and os.path.exists(self.CACHE_FILE):
            age_seconds = time.time() - os.path.getmtime(self.CACHE_FILE)
            if age_seconds < self.CACHE_DURATION_HOURS * 3600:
                try:
                    with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                        self.events = json.load(f)
                    print(f"[CACHE] Loaded {len(self.events)} events from local cache.")
                    return self.events
                except Exception:
                    pass

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        req = urllib.request.Request(self.CALENDAR_URL, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8")
                self.events = json.loads(content)
                with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                    f.write(content)
            print(f"[LIVE] Downloaded {len(self.events)} fresh events from Forex Factory.")
            return self.events
        except Exception as e:
            print(f"[WARN] Live fetch failed ({e}). Attempting to use local cache...")
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    self.events = json.load(f)
                return self.events
            return []

    def get_high_impact_gold_events(self):
        """Filter events that strongly move Gold (USD / High Impact)."""
        if not self.events:
            self.fetch_calendar()

        filtered = []
        for event in self.events:
            country = event.get("country", "")
            impact = event.get("impact", "")
            if country in self.target_currencies and impact == self.min_impact:
                filtered.append(event)
        return filtered

    def check_blackout_status(self, buffer_minutes=15):
        """
        Checks if the current time falls within `buffer_minutes` before or after
        any High-Impact USD news event.
        Returns: (is_blackout: bool, event_details: dict or None)
        """
        now = datetime.now(timezone.utc)
        high_impact = self.get_high_impact_gold_events()

        for event in high_impact:
            date_str = event.get("date")
            if not date_str:
                continue

            event_time = datetime.fromisoformat(date_str).astimezone(timezone.utc)
            diff_seconds = (event_time - now).total_seconds()
            diff_minutes = diff_seconds / 60.0

            # If within window: -buffer_minutes <= diff_minutes <= buffer_minutes
            if -buffer_minutes <= diff_minutes <= buffer_minutes:
                return True, {
                    "title": event.get("title"),
                    "country": event.get("country"),
                    "event_time": event_time.isoformat(),
                    "minutes_until_event": round(diff_minutes, 1),
                    "forecast": event.get("forecast"),
                    "previous": event.get("previous"),
                }

        return False, None


if __name__ == "__main__":
    engine = ForexFactoryEngine()
    print("Fetching Forex Factory calendar events...")
    events = engine.fetch_calendar()
    print(f"Total events loaded this week: {len(events)}")

    high_impact = engine.get_high_impact_gold_events()
    print(f"\n--- HIGH IMPACT USD/EUR GOLD DRIVERS THIS WEEK ({len(high_impact)} events) ---")
    for ev in high_impact[:10]:
        print(f"[{ev['country']}] {ev['date']} | {ev['title']} | Forecast: {ev.get('forecast')} | Prev: {ev.get('previous')}")

    is_blackout, details = engine.check_blackout_status(buffer_minutes=15)
    print("\n--- TRAJEDOR BLACKOUT GUARD STATUS ---")
    if is_blackout:
        print(f"[!] BLACKOUT ACTIVE: Trading halted due to {details['title']} in {details['minutes_until_event']} mins.")
    else:
        print("[OK] MARKET CLEAR: No immediate high-impact USD events in the next 15-minute window.")
