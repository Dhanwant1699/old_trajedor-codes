"""
Trajedor Social Sentiment & Trader Monitoring Engine
Tracks live gold trader sentiment from:
1. Stocktwits live ticker streams ($GLD, $GOLD) - Free, zero login required.
2. X (Twitter) monitored accounts - Uses local session credentials from .env.
"""

import os
import json
import urllib.request
from datetime import datetime


class SocialTraderTracker:
    STOCKTWITS_API = "https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"

    # Keywords for sentiment classification
    BULLISH_KEYWORDS = ["buy", "long", "call", "moon", "breakout", "rally", "bounce", "bull", "ath"]
    BEARISH_KEYWORDS = ["sell", "short", "put", "dump", "crash", "resistance", "bear", "plunge", "top"]

    def __init__(self, target_symbols=None, monitored_x_traders=None):
        self.target_symbols = target_symbols or ["GLD"]
        self.monitored_x_traders = monitored_x_traders or [
            "GoldTelegraph_", "Fxhedgers", "unusual_whales", "zerohedge"
        ]

    def fetch_stocktwits_sentiment(self, symbol="GLD"):
        """
        Fetches the latest public comments and sentiment for Gold on Stocktwits.
        Does not require any login or API key.
        """
        url = self.STOCKTWITS_API.format(symbol=symbol)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                messages = data.get("messages", [])
                
                bullish_count = 0
                bearish_count = 0
                parsed_posts = []

                for msg in messages:
                    body = msg.get("body", "")
                    entities = msg.get("entities", {})
                    sentiment = entities.get("sentiment", {})
                    basic_sentiment = sentiment.get("basic") if sentiment else None

                    # If user tagged sentiment explicitly
                    if basic_sentiment == "Bullish":
                        bullish_count += 1
                    elif basic_sentiment == "Bearish":
                        bearish_count += 1
                    else:
                        # Fallback to keyword matching
                        body_lower = body.lower()
                        b_score = sum(1 for kw in self.BULLISH_KEYWORDS if kw in body_lower)
                        s_score = sum(1 for kw in self.BEARISH_KEYWORDS if kw in body_lower)
                        if b_score > s_score:
                            bullish_count += 1
                        elif s_score > b_score:
                            bearish_count += 1

                    parsed_posts.append({
                        "user": msg.get("user", {}).get("username"),
                        "created_at": msg.get("created_at"),
                        "body": body,
                        "sentiment": basic_sentiment or "Neutral/Mixed"
                    })

                total = bullish_count + bearish_count
                bull_ratio = (bullish_count / total * 100) if total > 0 else 50.0

                return {
                    "symbol": symbol,
                    "total_messages": len(messages),
                    "bullish": bullish_count,
                    "bearish": bearish_count,
                    "bullish_percentage": round(bull_ratio, 1),
                    "posts": parsed_posts[:5]  # Top 5 most recent
                }
        except Exception as e:
            print(f"[ERROR] Stocktwits fetch failed for {symbol}: {e}")
            return None

    def scan_x_traders_instructions(self):
        """
        Instructions and status for X (Twitter) trader monitoring.
        """
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        has_env = os.path.exists(env_path)

        return {
            "configured": has_env,
            "target_accounts": self.monitored_x_traders,
            "note": "X automation uses local credentials stored in your private .env file."
        }


if __name__ == "__main__":
    tracker = SocialTraderTracker()
    print("--- SCANNING LIVE GOLD TRADER SENTIMENT (Stocktwits) ---")
    results = tracker.fetch_stocktwits_sentiment("GLD")
    
    if results:
        print(f"Asset: {results['symbol']}")
        print(f"Total Sampled Messages: {results['total_messages']}")
        print(f"Bullish Posts: {results['bullish']} | Bearish Posts: {results['bearish']}")
        print(f"Crowd Sentiment: {results['bullish_percentage']}% BULLISH")
        print("\nRecent Trader Comments:")
        for post in results['posts']:
            clean_body = post['body'][:90].encode('ascii', 'ignore').decode('ascii')
            print(f"- @{post['user']} [{post['sentiment']}]: {clean_body}...")
    else:
        print("Could not retrieve sentiment at this moment.")

    x_status = tracker.scan_x_traders_instructions()
    print("\n--- X (TWITTER) TRADER MONITOR STATUS ---")
    print(f"Local .env Configured: {x_status['configured']}")
    print(f"Target Traders to Track: {', '.join(x_status['target_accounts'])}")
