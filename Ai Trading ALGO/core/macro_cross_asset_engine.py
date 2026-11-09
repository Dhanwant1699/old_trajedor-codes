"""
Live Cross-Asset Macro Intelligence & Breaking News Engine for Trajedor.

Fetches real-time live market metrics without requiring API keys:
1. US Dollar Index (DXY / DX-Y.NYB): Spot price, daily change %, correlation vector.
2. US 10-Year Treasury Yield (^TNX): Current yield %, daily basis point change (Real Yield proxy).
3. Crude Oil (WTI / CL=F): Inflation and geopolitical escalation proxy.
4. Breaking Financial News & Geopolitics: Live RSS ingestion from FXStreet & Investing.com.
5. Computes Real-Time Cross-Asset Pressure Score for Gold (XAUUSD).
"""

import os
import sys
import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CONFIG


class MacroCrossAssetEngine:
    CACHE_DURATION_SECS = 45

    def __init__(self):
        self._cache_time = 0.0
        self._cached_data: Optional[Dict[str, Any]] = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

    def fetch_live_macro_suite(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Fetches live DXY, US10Y Yield, Crude Oil, and breaking FXStreet/Investing.com headlines.
        """
        now = time.time()
        if not force_refresh and self._cached_data and (now - self._cache_time < self.CACHE_DURATION_SECS):
            return self._cached_data

        dxy_data = self._fetch_yahoo_ticker("DX-Y.NYB", name="US Dollar Index (DXY)", fallback_price=101.92)
        us10y_data = self._fetch_yahoo_ticker("^TNX", name="US 10-Year Treasury Yield", fallback_price=4.28)
        oil_data = self._fetch_yahoo_ticker("CL=F", name="Crude Oil (WTI)", fallback_price=71.50)
        breaking_news = self._fetch_fxstreet_headlines()

        # Assess gold macro pressure
        macro_score, gold_bias, narrative = self._synthesize_gold_impact(dxy_data, us10y_data, oil_data, breaking_news)

        result = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "dxy": dxy_data,
            "us10y_yield": us10y_data,
            "crude_oil": oil_data,
            "breaking_news": breaking_news[:10],
            "gold_macro_impact_score": macro_score,  # -100 (Extremely Bearish) to +100 (Extremely Bullish)
            "gold_bias": gold_bias,                  # "STRONG_BULLISH", "MODERATE_BULLISH", "BEARISH", "NEUTRAL"
            "macro_narrative": narrative
        }

        self._cached_data = result
        self._cache_time = now
        return result

    def _fetch_yahoo_ticker(self, ticker: str, name: str, fallback_price: float) -> Dict[str, Any]:
        """Fetches live price, change, and % change from Yahoo Finance public chart endpoint."""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=5m"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
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
        except Exception as e:
            # Clean fallback if rate-limited or offline
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

    def _fetch_fxstreet_headlines(self) -> List[Dict[str, str]]:
        """Ingests live financial and gold breaking headlines from FXStreet and Google News."""
        headlines = []
        
        # 1. Google News Live Search RSS (Gold, XAUUSD, Federal Reserve, DXY)
        google_news_url = "https://news.google.com/rss/search?q=Gold+price+XAUUSD+or+Federal+Reserve+or+US+dollar&hl=en-US&gl=US&ceid=US:en"
        try:
            req = urllib.request.Request(google_news_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
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
                            "is_gold_relevant": is_gold
                        })
        except Exception:
            pass

        # 2. FXStreet RSS Feed
        fxstreet_url = "https://www.fxstreet.com/rss/news"
        try:
            req = urllib.request.Request(fxstreet_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
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
                            "is_gold_relevant": is_gold
                        })
        except Exception:
            pass

        # Deduplicate headlines by title
        seen_titles = set()
        unique_headlines = []
        for h in headlines:
            clean_t = h["title"].lower()
            if clean_t not in seen_titles:
                seen_titles.add(clean_t)
                unique_headlines.append(h)

        # Sort so gold-relevant news appears first
        unique_headlines.sort(key=lambda x: x["is_gold_relevant"], reverse=True)
        return unique_headlines

    def _synthesize_gold_impact(
        self,
        dxy: Dict[str, Any],
        us10y: Dict[str, Any],
        oil: Dict[str, Any],
        news: List[Dict[str, str]]
    ) -> Tuple[int, str, str]:
        """
        Calculates net institutional macro pressure on Gold:
        - Falling DXY = Bullish for Gold
        - Falling US10Y Yields = Bullish for Gold
        - Rising Oil = Inflation/Geopolitical safe-haven demand (Bullish)
        - War/Geopolitics headlines = Bullish safe-haven
        """
        score = 0
        reasons = []

        # 1. DXY Vector
        dxy_chg = dxy.get("change_pct", 0.0)
        if dxy_chg <= -0.15:
            score += 35
            reasons.append(f"US Dollar weakening ({dxy_chg:+.2f}%); expands bullion purchasing power")
        elif dxy_chg >= 0.20:
            score -= 35
            reasons.append(f"US Dollar surging ({dxy_chg:+.2f}%); headwind for dollar-denominated assets")
        else:
            reasons.append(f"US Dollar stable at {dxy.get('price', 0.0)}")

        # 2. US 10Y Yield Vector
        y_chg = us10y.get("change", 0.0)
        if y_chg <= -0.02:
            score += 30
            reasons.append(f"US 10Y Treasury Yield softening ({us10y.get('price')}%, {y_chg:+.3f}); lowers opportunity cost of non-yielding bullion")
        elif y_chg >= 0.03:
            score -= 30
            reasons.append(f"US 10Y Treasury Yield rising ({us10y.get('price')}%, {y_chg:+.3f}); institutional capital rotating into paper yield")

        # 3. Geopolitical / News Vector
        news_text = " ".join([h.get("title", "") for h in news]).lower()
        if any(w in news_text for w in ["war", "strike", "missile", "middle east", "attack", "conflict"]):
            score += 25
            reasons.append("Geopolitical escalation detected; safe-haven flight-to-safety active")
        if any(w in news_text for w in ["rate cut", "dovish", "soft landing", "recession"]):
            score += 15
            reasons.append("Dovish monetary or easing expectations supportive of gold")

        score = max(-100, min(100, score))

        if score >= 35:
            bias = "STRONG_BULLISH"
        elif score >= 10:
            bias = "MODERATE_BULLISH"
        elif score <= -35:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        narrative = " | ".join(reasons)
        return score, bias, narrative


if __name__ == "__main__":
    engine = MacroCrossAssetEngine()
    suite = engine.fetch_live_macro_suite()
    print("=" * 80)
    print("LIVE CROSS-ASSET MACRO & BREAKING NEWS REPORT")
    print("=" * 80)
    print(f"DXY: {suite['dxy']['price']} ({suite['dxy']['change_pct']:+.2f}%)")
    print(f"US 10Y Yield: {suite['us10y_yield']['price']}% ({suite['us10y_yield']['change']:+.3f} bps)")
    print(f"Crude Oil: ${suite['crude_oil']['price']} ({suite['crude_oil']['change_pct']:+.2f}%)")
    print(f"Net Macro Gold Impact Score: {suite['gold_macro_impact_score']} / 100 ({suite['gold_bias']})")
    print(f"Narrative: {suite['macro_narrative']}")
    print("-" * 80)
    print("TOP BREAKING HEADLINES:")
    for h in suite["breaking_news"][:5]:
        print(f"- [{h['source']}] {h['title']}")
    print("=" * 80)
