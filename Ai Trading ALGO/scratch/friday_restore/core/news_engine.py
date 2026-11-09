"""
News and Macroeconomic Sentiment Engine for Claude XAUUSD AI Trader.
Powered by:
- ForexFactory.com: Real-time high-impact economic calendar events & forecasts.
- Investing.com: Real-time Commodities (Gold/XAU), Forex (USD/DXY), and Macro analysis feeds.
"""

import io
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
import requests
import xml.etree.ElementTree as ET

# Ensure UTF-8 console output on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from config import CONFIG


INVESTING_FEEDS = [
    {"name": "Investing.com Commodities (Gold)", "url": "https://www.investing.com/rss/news_11.rss", "category": "COMMODITIES_GOLD"},
    {"name": "Investing.com Forex & USD", "url": "https://www.investing.com/rss/news_1.rss", "category": "FOREX_USD"},
    {"name": "Investing.com Economy & Macro", "url": "https://www.investing.com/rss/news_14.rss", "category": "ECONOMY_MACRO"},
    {"name": "Investing.com Market Overview", "url": "https://www.investing.com/rss/market_overview.rss", "category": "MARKET_OVERVIEW"},
]

FOREXFACTORY_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


class ForexNewsEngine:
    """
    Ingests live economic events and news headlines from ForexFactory.com and Investing.com.
    """
    def __init__(self):
        self.cached_calendar: List[Dict[str, Any]] = []
        self.last_calendar_fetch: Optional[datetime] = None
        self.cached_headlines: List[Dict[str, str]] = []
        self.last_news_fetch: Optional[datetime] = None

        self.http_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def fetch_forexfactory_calendar(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetches this week's economic calendar events from ForexFactory.com syndication feed.
        """
        now = datetime.now(timezone.utc)
        # Cache for 20 minutes
        if not force_refresh and self.last_calendar_fetch and (now - self.last_calendar_fetch).total_seconds() < 1200:
            return self.cached_calendar

        events = []
        try:
            resp = requests.get(FOREXFACTORY_CALENDAR_URL, headers=self.http_headers, timeout=10)
            if resp.status_code == 200:
                raw_events = resp.json()
                for item in raw_events:
                    currency = item.get("country", "")
                    impact = item.get("impact", "")
                    # Filter USD events with High, Medium or Holiday impact
                    if currency in ["USD", "ALL"] and impact in ["High", "Medium", "Holiday"]:
                        date_str = item.get("date", "")
                        try:
                            dt = datetime.fromisoformat(date_str)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            else:
                                dt = dt.astimezone(timezone.utc)
                        except Exception:
                            dt = now

                        events.append({
                            "source": "ForexFactory.com",
                            "title": item.get("title", ""),
                            "currency": currency,
                            "impact": impact,
                            "event_time_utc": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "event_dt": dt,
                            "forecast": item.get("forecast", ""),
                            "previous": item.get("previous", ""),
                        })

                self.cached_calendar = events
                self.last_calendar_fetch = now
                print(f"[NewsEngine - ForexFactory.com] Loaded {len(events)} USD/Global calendar events.")
        except Exception as e:
            print(f"[NewsEngine - ForexFactory.com] Calendar fetch error: {e}")

        return self.cached_calendar

    def fetch_investing_headlines(self, force_refresh: bool = False) -> List[Dict[str, str]]:
        """
        Fetches real-time financial, forex, and commodities headlines directly from Investing.com RSS feeds.
        """
        now = datetime.now(timezone.utc)
        if not force_refresh and self.last_news_fetch and (now - self.last_news_fetch).total_seconds() < 600:
            return self.cached_headlines

        parsed_items: List[Dict[str, str]] = []
        gold_usd_keywords = [
            "gold", "xau", "bullion", "precious metals",
            "dollar", "usd", "dxy", "greenback", "fed", "powell", "fomc",
            "rate", "inflation", "cpi", "ppi", "treasury", "yield",
            "geopolitical", "safe haven", "central bank"
        ]

        for feed in INVESTING_FEEDS:
            try:
                resp = requests.get(feed["url"], headers=self.http_headers, timeout=8)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    for item in root.findall(".//item"):
                        title_el = item.find("title")
                        pub_date_el = item.find("pubDate")
                        title = title_el.text.strip() if title_el is not None and title_el.text else ""
                        pub_date = pub_date_el.text.strip() if pub_date_el is not None and pub_date_el.text else ""

                        if not title:
                            continue

                        # Prioritize headlines mentioning Gold, USD, Fed, Macro
                        is_relevant = any(kw in title.lower() for kw in gold_usd_keywords)
                        if is_relevant or feed["category"] == "COMMODITIES_GOLD":
                            parsed_items.append({
                                "source": "Investing.com",
                                "feed": feed["name"],
                                "title": title,
                                "pub_date": pub_date,
                                "is_high_relevance": is_relevant
                            })
            except Exception as e:
                continue

        # Sort with high relevance first, deduplicate by title
        seen_titles = set()
        deduped = []
        for item in parsed_items:
            if item["title"] not in seen_titles:
                seen_titles.add(item["title"])
                deduped.append(item)

        if not deduped:
            deduped = [{
                "source": "Investing.com",
                "feed": "General",
                "title": "Markets calm; monitoring USD yields and gold liquidity.",
                "pub_date": now.strftime("%Y-%m-%d %H:%M:%S"),
                "is_high_relevance": False
            }]

        self.cached_headlines = deduped[:12]  # Keep top 12 curated stories
        self.last_news_fetch = now
        print(f"[NewsEngine - Investing.com] Fetched {len(self.cached_headlines)} real-time headlines.")
        return self.cached_headlines

    def check_news_blackout(self, window_minutes: int = CONFIG.NEWS_BLACKOUT_MINUTES) -> Tuple[bool, Optional[str]]:
        """
        Checks ForexFactory calendar for imminent or recent HIGH IMPACT (Red Folder) USD releases.
        Returns: (is_blackout, reason_description)
        """
        if not CONFIG.ENABLE_NEWS_FILTER:
            return False, None

        events = self.fetch_forexfactory_calendar()
        now_utc = datetime.now(timezone.utc)

        for ev in events:
            if ev.get("impact") == "High" and ev.get("currency") == "USD":
                event_dt: datetime = ev.get("event_dt", now_utc)
                diff_minutes = (event_dt - now_utc).total_seconds() / 60.0

                if -window_minutes <= diff_minutes <= window_minutes:
                    if diff_minutes > 0:
                        reason = f"[ForexFactory Alert] High-impact event '{ev['title']}' scheduled in {int(diff_minutes)} mins ({ev['event_time_utc']})"
                    else:
                        reason = f"[ForexFactory Alert] High-impact event '{ev['title']}' released {int(abs(diff_minutes))} mins ago ({ev['event_time_utc']})"
                    return True, reason

        return False, None

    def get_news_payload(self) -> Dict[str, Any]:
        """
        Aggregates ForexFactory.com economic calendar and Investing.com live news
        into a structured payload for Claude.
        """
        events = self.fetch_forexfactory_calendar()
        headlines = self.fetch_investing_headlines()
        is_blackout, blackout_reason = self.check_news_blackout()

        now_utc = datetime.now(timezone.utc)
        upcoming_24h = []
        for ev in events:
            event_dt = ev.get("event_dt", now_utc)
            hours_away = (event_dt - now_utc).total_seconds() / 3600.0
            if 0 <= hours_away <= 24:
                upcoming_24h.append({
                    "source": "ForexFactory.com",
                    "time_utc": ev["event_time_utc"],
                    "event": ev["title"],
                    "impact": ev["impact"],
                    "forecast": ev.get("forecast", "-"),
                    "previous": ev.get("previous", "-")
                })

        return {
            "sources": ["https://www.forexfactory.com", "https://www.investing.com"],
            "news_blackout_active": is_blackout,
            "blackout_reason": blackout_reason,
            "forexfactory_upcoming_events": upcoming_24h[:8],
            "investing_com_realtime_news": [
                f"[{item['source']} - {item['feed']}] {item['title']} ({item.get('pub_date', '')})"
                for item in headlines
            ]
        }
