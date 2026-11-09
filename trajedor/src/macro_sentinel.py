"""
TRAJEDOR - Live Macro Sentinel & Breaking News Engine.
Fetches real-time cross-asset drivers without API keys:
1. US Dollar Index (DXY)
2. US 10-Year Treasury Yield (^TNX)
3. Crude Oil (WTI / CL=F)
4. Google News Search RSS & FXStreet Breaking Feeds
"""

import time
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple


class MacroSentinel:
    CACHE_DURATION_SECS = 45

    def __init__(self):
        self._cache_time = 0.0
        self._cached_data: Dict[str, Any] = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

    def get_live_macro_suite(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Returns live macro drivers, threat score, and breaking news."""
        now = time.time()
        if not force_refresh and self._cached_data and (now - self._cache_time < self.CACHE_DURATION_SECS):
            return self._cached_data

        dxy = self._fetch_yahoo_ticker("DX-Y.NYB", name="US Dollar Index (DXY)", fallback_price=101.92)
        us10y = self._fetch_yahoo_ticker("^TNX", name="US 10-Year Treasury Yield", fallback_price=5.28)
        oil = self._fetch_yahoo_ticker("CL=F", name="Crude Oil (WTI)", fallback_price=91.11)
        news = self._fetch_live_breaking_news()

        score, bias, narrative = self._synthesize_gold_impact(dxy, us10y, oil, news)

        result = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "dxy": dxy,
            "us10y_yield": us10y,
            "crude_oil": oil,
            "breaking_news": news[:12],
            "gold_macro_impact_score": score,
            "gold_bias": bias,
            "macro_narrative": narrative
        }

        self._cached_data = result
        self._cache_time = now
        return result

    def _fetch_yahoo_ticker(self, ticker: str, name: str, fallback_price: float) -> Dict[str, Any]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=5m"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                result = data.get("chart", {}).get("result", [])
                if result:
                    meta = result[0].get("meta", {})
                    price = float(meta.get("regularMarketPrice", fallback_price) or fallback_price)
                    prev_close = float(meta.get("chartPreviousClose", price) or price)
                    change = round(price - prev_close, 3)
                    pct_change = round((change / prev_close) * 100.0, 2) if prev_close else 0.0

                    return {
                        "ticker": ticker,
                        "name": name,
                        "price": round(price, 3),
                        "previous_close": round(prev_close, 3),
                        "change": change,
                        "change_pct": pct_change,
                        "trend": "UP" if change > 0 else ("DOWN" if change < 0 else "FLAT"),
                        "status": "LIVE"
                    }
        except Exception:
            pass

        return {
            "ticker": ticker,
            "name": name,
            "price": fallback_price,
            "previous_close": fallback_price,
            "change": 0.0,
            "change_pct": 0.0,
            "trend": "FLAT",
            "status": "FALLBACK"
        }

    def _fetch_live_breaking_news(self) -> List[Dict[str, Any]]:
        headlines = []
        
        # 1. Google News Live Search RSS
        google_news_url = "https://news.google.com/rss/search?q=Gold+price+XAUUSD+or+Federal+Reserve+or+US+dollar&hl=en-US&gl=US&ceid=US:en"
        try:
            req = urllib.request.Request(google_news_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                root = ET.fromstring(resp.read())
                for item in root.findall(".//item")[:10]:
                    title = item.find("title").text if item.find("title") is not None else ""
                    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                    source_elem = item.find("source")
                    source_name = source_elem.text if source_elem is not None else "Google News"
                    if title:
                        is_gold = any(k in title.lower() for k in ["gold", "xau", "bullion", "metal", "yield", "dollar", "fed", "powell"])
                        headlines.append({
                            "source": source_name,
                            "title": title.strip(),
                            "pub_date": pub_date.strip(),
                            "is_gold": is_gold
                        })
        except Exception:
            pass

        # 2. FXStreet RSS Feed
        fxstreet_url = "https://www.fxstreet.com/rss/news"
        try:
            req = urllib.request.Request(fxstreet_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                root = ET.fromstring(resp.read())
                for item in root.findall(".//item")[:10]:
                    title = item.find("title").text if item.find("title") is not None else ""
                    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                    if title:
                        is_gold = any(k in title.lower() for k in ["gold", "xau", "bullion", "metal", "yield", "dollar", "fed", "powell"])
                        headlines.append({
                            "source": "FXStreet",
                            "title": title.strip(),
                            "pub_date": pub_date.strip(),
                            "is_gold": is_gold
                        })
        except Exception:
            pass

        # Deduplicate
        seen = set()
        deduped = []
        for h in headlines:
            clean = h["title"].lower()
            if clean not in seen:
                seen.add(clean)
                deduped.append(h)

        deduped.sort(key=lambda x: x["is_gold"], reverse=True)
        return deduped

    def _synthesize_gold_impact(self, dxy: Dict[str, Any], us10y: Dict[str, Any], oil: Dict[str, Any], news: List[Dict[str, Any]]) -> Tuple[int, str, str]:
        score = 0
        narrative_parts = []

        dxy_chg = dxy.get("change_pct", 0.0)
        if dxy_chg <= -0.15:
            score += 35
            narrative_parts.append(f"DXY weakening ({dxy_chg:+.2f}%) expands bullion purchasing power")
        elif dxy_chg >= 0.20:
            score -= 35
            narrative_parts.append(f"DXY surging ({dxy_chg:+.2f}%) dollar-denominated headwind")
        else:
            narrative_parts.append(f"DXY stable at {dxy.get('price')}")

        y_chg = us10y.get("change", 0.0)
        if y_chg <= -0.02:
            score += 30
            narrative_parts.append(f"US 10Y Yield softening ({us10y.get('price')}%, {y_chg:+.3f}); lowers bullion opportunity cost")
        elif y_chg >= 0.03:
            score -= 30
            narrative_parts.append(f"US 10Y Yield elevated ({us10y.get('price')}%, {y_chg:+.3f}); paper yield capital rotation")

        news_text = " ".join([h.get("title", "") for h in news]).lower()
        if any(w in news_text for w in ["war", "strike", "missile", "middle east", "attack", "conflict"]):
            score += 25
            narrative_parts.append("Geopolitical escalation detected: safe-haven bullion demand active")
        if any(w in news_text for w in ["rate cut", "dovish", "soft landing"]):
            score += 15
            narrative_parts.append("Dovish monetary expectations supportive")

        score = max(-100, min(100, score))
        if score >= 35:
            bias = "STRONG_BULLISH"
        elif score >= 10:
            bias = "MODERATE_BULLISH"
        elif score <= -35:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        return score, bias, " | ".join(narrative_parts)
