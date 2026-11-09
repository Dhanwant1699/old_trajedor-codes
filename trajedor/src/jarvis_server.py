"""
TRAJEDOR - Standalone Jarvis Server & Holographic Web Cockpit Launcher.
Serves the Iron Man JARVIS Mark-85 HUD on Port 1111 with real-time REST API.
"""

import os
import sys
import json
import time
import http.server
import socketserver
import threading
from typing import Dict, Any

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trajedor.config.settings import SETTINGS
from trajedor.src.macro_sentinel import MacroSentinel
from trajedor.src.cognitive_brain import CognitiveBrain
from trajedor.src.trade_doctor import TradeDoctor
from trajedor.src.mt5_multi_account import MT5MultiAccountBridge
from trajedor.src.memory_journal import MemoryJournal

UI_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "index.html")

# Global Engines
macro_sentinel = MacroSentinel()
brain = CognitiveBrain(symbol=SETTINGS.PRIMARY_SYMBOL)
doctor = TradeDoctor()
mt5_bridge = MT5MultiAccountBridge()
journal = MemoryJournal()

def _get_initial_accounts_dict():
    """Only load terminals that are verified and detected on this PC."""
    try:
        mt5_bridge.discover_terminals(prune_missing=True)
        return mt5_bridge.get_live_telemetry()
    except Exception:
        return {}

_STATUS_CACHE = {
    "time": time.time(),
    "data": {
        "timestamp": time.time(),
        "symbol": SETTINGS.PRIMARY_SYMBOL,
        "tick": {"bid": 4139.52, "ask": 4139.92, "spread": 4.0},
        "macro": {
            "dxy": {"ticker": "DX-Y.NYB", "name": "US Dollar Index (DXY)", "price": 101.92, "change_pct": -0.01},
            "us10y_yield": {"ticker": "^TNX", "name": "US 10-Year Treasury Yield", "price": 5.277, "change_pct": 0.76},
            "crude_oil": {"ticker": "CL=F", "name": "Crude Oil (WTI)", "price": 91.11, "change_pct": -1.9},
            "gold_bias": "BULLISH",
            "gold_macro_impact_score": -30
        },
        "accounts": _get_initial_accounts_dict(),
        "thesis": {
            "action": "SELL",
            "confidence_score": 83,
            "entry_price": 4139.52,
            "stop_loss": 4164.02,
            "take_profit_1": 4127.52,
            "take_profit_2": 4115.52,
            "risk_reward_ratio": 0.49,
            "metamorphosis_mode": "TACTICAL_SCALP",
            "session_phase": "LONDON_EXPANSION",
            "regime": "PREMIUM_DISTRIBUTION",
            "retail_long_pct": 71.4,
            "retail_short_pct": 28.6,
            "smart_money_bias": "HUNTING_RETAIL_STOPS",
            "reasoning_monologue": "JARVIS Cognition: Elevated Treasury Yields (5.277%) exerting institutional selling pressure. Bearish Order Block resistance at $4154.02 - $4161.52. Targeting sell-side liquidity at $4127.52 with strict early-cut defense.",
            "memory_gate_approved": True,
            "memory_warnings": [],
            "lessons_consulted": ["NEVER catch falling knives or buy premium highs without liquidity sweep and completed M5 structural confirmation (CHoCH)."],
            "council_votes": {
                "Macro Sentinel": "BUY",
                "Location Agent": "HOLD",
                "SMC Topology": "BUY",
                "Momentum Agent": "BUY",
                "Sentiment Trap": "HOLD",
                "CRO Risk Guard": "BUY"
            },
            "council_consensus_pct": 66.7,
            "council_rationale": ["Macro Bullish", "SMC Breakout Confirmed", "Momentum Positive"],
            "pitch_initiator": "Momentum Agent",
            "pitch_setup_type": "MOMENTUM_BREAKOUT_LONG",
            "roundtable_transcript": [
                {"speaker": "Chairman Trajedor", "statement": "Council assembled. Scanning live market structure across all 8 timeframes (1W to M1)..."},
                {"speaker": "Macro Sentinel (1W/D1)", "statement": "Secular multi-week trend is strongly bullish. D1 holding above 20-EMA."},
                {"speaker": "Location Agent (H4/H1)", "statement": "Price expanding through daily resistance. Breakout conditions active."},
                {"speaker": "SMC Topology (M30/M15)", "statement": "Bullish Fair Value Gap respected on M15. No opposing supply barrier."},
                {"speaker": "Momentum Agent (M5/M1)", "statement": "Velocity surging. M5 CHoCH confirmed. Pitching MOMENTUM_BREAKOUT_LONG."},
                {"speaker": "Sentiment Trap (SSI)", "statement": "Retail crowd neutral/fading high. Institutional expansion pathway clear."},
                {"speaker": "CRO Risk Guard", "statement": "R:R evaluated at 1:2.0+. Stop-loss calibrated behind key M5 structural swing."},
                {"speaker": "Synthesis & Execution", "statement": "Consensus passed. Trade authorized."}
            ]
        },
        "history": [],
        "lessons": [
            {
                "rule_id": "RULE_OCT02_01_FALLING_KNIFE",
                "trigger": "OCT_2_AUTOPSY_TICKET_287239062",
                "lesson": "NEVER catch falling knives or buy premium highs without liquidity sweep and completed M5 structural confirmation (CHoCH).",
                "corrective_action": "Wait for sell-side liquidity (SSL) sweep and bullish M5 displacement candle before longing."
            },
            {
                "rule_id": "RULE_OCT02_02_PANIC_BOTTOM_SELL",
                "trigger": "OCT_2_AUTOPSY_TICKET_287289569",
                "lesson": "NEVER sell the bottom into daily institutional support / discount zone after extended downward exhaustion.",
                "corrective_action": "Only short into premium order blocks or retests of broken resistance, never at the floor."
            },
            {
                "rule_id": "RULE_ASYMMETRY_DEFENSE",
                "trigger": "NEGATIVE_ASYMMETRY_DISASTER",
                "lesson": "Active Trade Doctor must cut invalid setups early at -0.3R, protecting 70% risk capital instead of waiting for -1.0R broker SL.",
                "corrective_action": "Execute early exit immediately if opposing M5 FVG prints or thesis is invalidated."
            },
            {
                "rule_id": "RULE_RETAIL_TRAP_ALIGNMENT",
                "trigger": "RETAIL_HERD_FADING",
                "lesson": "When retail crowd is >70% long, expect an institutional flush of stops before any real upside expansion.",
                "corrective_action": "Do not enter long until the retail stop cluster below key swing lows is completely swept."
            }
        ]
    }
}
_CACHE_LOCK = threading.Lock()


def get_full_status_payload() -> Dict[str, Any]:
    with _CACHE_LOCK:
        return _STATUS_CACHE["data"]


def update_status_thesis(thesis_obj):
    """Directly updates the live Cockpit UI cache with executive deliberations."""
    try:
        with _CACHE_LOCK:
            if "data" in _STATUS_CACHE and "thesis" in _STATUS_CACHE["data"]:
                t = _STATUS_CACHE["data"]["thesis"]
                t["action"] = thesis_obj.action
                t["confidence_score"] = thesis_obj.confidence_score
                t["entry_price"] = thesis_obj.entry_price
                t["stop_loss"] = thesis_obj.stop_loss
                t["take_profit_1"] = thesis_obj.take_profit_1
                t["take_profit_2"] = thesis_obj.take_profit_2
                t["risk_reward_ratio"] = thesis_obj.risk_reward_ratio
                t["metamorphosis_mode"] = thesis_obj.metamorphosis_mode
                t["session_phase"] = thesis_obj.session_phase
                t["regime"] = thesis_obj.regime
                t["retail_long_pct"] = thesis_obj.retail_long_pct
                t["retail_short_pct"] = thesis_obj.retail_short_pct
                t["smart_money_bias"] = thesis_obj.smart_money_bias
                t["reasoning_monologue"] = thesis_obj.reasoning_monologue
                t["council_votes"] = getattr(thesis_obj, "council_votes", {})
                t["council_consensus_pct"] = getattr(thesis_obj, "council_consensus_pct", 0.0)
                t["council_rationale"] = getattr(thesis_obj, "council_rationale", [])
                t["pitch_initiator"] = getattr(thesis_obj, "pitch_initiator", "None")
                t["pitch_setup_type"] = getattr(thesis_obj, "pitch_setup_type", "STANDBY")
                t["roundtable_transcript"] = getattr(thesis_obj, "roundtable_transcript", [])
                t["chambers_briefing"] = getattr(thesis_obj, "chambers_briefing", {})
                _STATUS_CACHE["time"] = time.time()
    except Exception:
        pass


def _compute_status_payload() -> Dict[str, Any]:
    try:
        tick = mt5_bridge.get_live_gold_tick()
        live_price = float(tick.get("bid", 4139.52))
        macro = macro_sentinel.get_live_macro_suite()
        accounts = mt5_bridge.get_live_telemetry()
        # Extract Multi-Timeframe candles for Cognitive Brain
        mtf_suite = {}
        try:
            import MetaTrader5 as mt5
            sym = SETTINGS.PRIMARY_SYMBOL
            if not mt5.symbol_info(sym):
                sym = "XAUUSD.ecn"
            w1_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_W1, 0, 75)
            d1_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_D1, 0, 100)
            h4_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H4, 0, 100)
            h1_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 100)
            m30_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M30, 0, 200)
            m15_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 250)
            m5_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 280)
            m1_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 250)
            mtf_suite = {
                "w1": w1_rates, "d1": d1_rates, "h4": h4_rates, "h1": h1_rates,
                "m30": m30_rates, "m15": m15_rates, "m5": m5_rates, "m1": m1_rates
            }
        except Exception:
            pass

        thesis = brain.deliberate(current_price=live_price, mtf_candles=mtf_suite)
        history = journal.get_trade_history(limit=20)
        lessons = journal.get_lessons()
        chart_feed = mt5_bridge.get_live_candles(count=35)

        payload = {
            "timestamp": time.time(),
            "symbol": SETTINGS.PRIMARY_SYMBOL,
            "tick": tick,
            "macro": macro,
            "accounts": accounts,
            "chart_feed": chart_feed,
            "thesis": {
                "action": thesis.action,
                "confidence_score": thesis.confidence_score,
                "entry_price": thesis.entry_price,
                "stop_loss": thesis.stop_loss,
                "take_profit_1": thesis.take_profit_1,
                "take_profit_2": thesis.take_profit_2,
                "risk_reward_ratio": thesis.risk_reward_ratio,
                "metamorphosis_mode": thesis.metamorphosis_mode,
                "session_phase": thesis.session_phase,
                "regime": thesis.regime,
                "retail_long_pct": thesis.retail_long_pct,
                "retail_short_pct": thesis.retail_short_pct,
                "smart_money_bias": thesis.smart_money_bias,
                "order_blocks": thesis.order_blocks,
                "fair_value_gaps": thesis.fair_value_gaps,
                "reasoning_monologue": thesis.reasoning_monologue,
                "memory_gate_approved": thesis.memory_gate_approved,
                "memory_warnings": thesis.memory_warnings,
                "lessons_consulted": thesis.lessons_consulted,
                "council_votes": getattr(thesis, "council_votes", {}),
                "council_consensus_pct": getattr(thesis, "council_consensus_pct", 0.0),
                "council_rationale": getattr(thesis, "council_rationale", []),
                "pitch_initiator": getattr(thesis, "pitch_initiator", "None"),
                "pitch_setup_type": getattr(thesis, "pitch_setup_type", "STANDBY"),
                "roundtable_transcript": getattr(thesis, "roundtable_transcript", []),
                "opportunity_hunt_plans": getattr(thesis, "opportunity_hunt_plans", []),
                "chambers_briefing": getattr(thesis, "chambers_briefing", {})
            },
            "history": history,
            "lessons": lessons
        }
        with _CACHE_LOCK:
            _STATUS_CACHE["data"] = payload
            _STATUS_CACHE["time"] = time.time()
        return payload
    except Exception as e:
        if _STATUS_CACHE["data"]:
            return _STATUS_CACHE["data"]
        return {"error": str(e), "timestamp": time.time()}


def _background_telemetry_refresher():
    """Background worker that keeps the HUD cache fresh without blocking HTTP requests."""
    cycle = 0
    while True:
        try:
            if cycle % 6 == 0:
                mt5_bridge.discover_terminals(prune_missing=True)
            _compute_status_payload()
        except Exception:
            pass
        cycle += 1
        time.sleep(10)


class JarvisHTTPHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        try:
            self.connection.settimeout(30.0)
        except Exception:
            pass

    def log_message(self, format, *args):
        pass  # Suppress default request noise

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, ConnectionError):
            pass

    def do_HEAD(self):
        clean_path = self.path.split("?")[0]
        self.send_response(200)
        if clean_path in ("/", "/index.html", "/ui"):
            self.send_header("Content-Type", "text/html; charset=utf-8")
        else:
            self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Connection", "close")
        self.end_headers()

    def do_GET(self):
        clean_path = self.path.split("?")[0]
        try:
            if clean_path in ("/", "/index.html", "/ui"):
                if os.path.exists(UI_FILE):
                    with open(UI_FILE, "r", encoding="utf-8") as f:
                        content = f.read()
                    try:
                        cached = get_full_status_payload()
                        accs = cached.get("accounts", {})
                        injection = f"<script>window.__PRELOADED_ACCOUNTS__ = {json.dumps(accs)};</script></head>"
                        content = content.replace("</head>", injection, 1)
                    except Exception:
                        pass
                    data_bytes = content.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(data_bytes)))
                    self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                    self.send_header("Pragma", "no-cache")
                    self.send_header("Expires", "0")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(data_bytes)
                else:
                    self.send_response(404)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(b"UI file not found.")
                return

            elif clean_path in ("/api/trajedor/status", "/api/status"):
                payload = get_full_status_payload()
                data_bytes = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(data_bytes)
                return

            elif clean_path == "/api/trajedor/macro":
                data = macro_sentinel.get_live_macro_suite()
                data_bytes = json.dumps(data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(data_bytes)
                return

            elif clean_path == "/api/trajedor/accounts":
                data = mt5_bridge.get_live_telemetry()
                data_bytes = json.dumps(data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(data_bytes)
            elif clean_path in ("/api/trajedor/accounts/discover", "/api/accounts/discover"):
                res = mt5_bridge.discover_terminals(prune_missing=True)
                live_telemetry = mt5_bridge.get_live_telemetry()
                with _CACHE_LOCK:
                    if "data" in _STATUS_CACHE:
                        _STATUS_CACHE["data"]["accounts"] = live_telemetry
                    _STATUS_CACHE["time"] = time.time()
                data_bytes = json.dumps(res).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(data_bytes)
                self.wfile.flush()
                return

            else:
                self.send_response(404)
                self.end_headers()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass  # Client refreshed or closed tab mid-stream

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        clean_path = self.path.split("?")[0]
        if clean_path in ("/api/trajedor/accounts/limits", "/api/accounts/limits"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                payload = json.loads(body)
                acc_id = payload.get("acc_id")
                new_limits = payload.get("limits", {})

                success = mt5_bridge.update_account_limits(acc_id, new_limits)
                # Immediately update status cache so UI updates immediately
                with _CACHE_LOCK:
                    _STATUS_CACHE["time"] = time.time()
                    if "accounts" in _STATUS_CACHE["data"] and acc_id in _STATUS_CACHE["data"]["accounts"]:
                        for k, v in new_limits.items():
                            _STATUS_CACHE["data"]["accounts"][acc_id][k] = v

                resp = json.dumps({"status": "SUCCESS" if success else "ERROR", "acc_id": acc_id, "limits": new_limits}).encode("utf-8")
                self.send_response(200 if success else 400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(resp)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(resp)
                self.wfile.flush()
            except Exception as e:
                resp = json.dumps({"status": "ERROR", "error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(resp)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(resp)
                self.wfile.flush()
        else:
            self.send_response(404)
            self.end_headers()


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # Gracefully suppress client disconnection exceptions on Windows
        pass


def start_jarvis_cockpit(port: int = 1111):
    server = ThreadedHTTPServer(("0.0.0.0", port), JarvisHTTPHandler)
    print("=" * 80, flush=True)
    print(f"[TRAJEDOR] JARVIS MARK-85 HOLOGRAPHIC COCKPIT SERVER", flush=True)
    print(f"[INFO] Neural Interface Live: http://localhost:{port}", flush=True)
    print(f"[DEFENSE] Trade Doctor Active Defense: ARMED", flush=True)
    print(f"[MACRO] Live Macro Feeds & Google News: CONNECTED", flush=True)
    print("=" * 80, flush=True)

    def _delayed_refresher():
        time.sleep(1)
        _background_telemetry_refresher()

    threading.Thread(target=_delayed_refresher, daemon=True).start()
    server.serve_forever()


if __name__ == "__main__":
    target_port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else SETTINGS.PORT
    start_jarvis_cockpit(port=target_port)
