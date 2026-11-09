"""
Quick launcher for the Real-Time AI Trading Dashboard UI
Accessible at http://localhost:2500
"""

import sys
import os
import json
import time
import threading
import http.server
import socketserver
from datetime import datetime, timezone
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import CONFIG
from core.council_state import CouncilStateManager
from core.dashboard_server import (
    get_real_mt5_trade_history,
    get_admin_config,
    scan_all_accounts,
    DASHBOARD_FILE,
    PORT,
    _LATEST_TICKS
)

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Request Handler for real-time dashboard"""

    def do_GET(self):
        """Handle GET requests"""
        try:
            if self.path == "/" or self.path == "/dashboard":
                # Serve HTML dashboard
                if os.path.exists(DASHBOARD_FILE):
                    with open(DASHBOARD_FILE, 'rb') as f:
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.end_headers()
                        self.wfile.write(f.read())
                        return
                else:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(b"<h1>AI Trading Dashboard</h1><p>Real-time monitoring UI loading...</p>")
                    return

            elif self.path == "/api/status":
                # Real-time market status
                state = CouncilStateManager.get_state()
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "symbols": state.get("symbols", {}),
                    "ticks": _LATEST_TICKS
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode('utf-8'))
                return

            elif self.path == "/api/trades":
                # Trade history
                trades = get_real_mt5_trade_history(days=30)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(trades).encode('utf-8'))
                return

            elif self.path == "/api/accounts":
                # Account telemetry - return config-based accounts without MT5 reinitialization
                try:
                    admin_cfg = get_admin_config()
                    accounts = {}
                    for acc_id, cfg in admin_cfg.get("accounts", {}).items():
                        accounts[acc_id] = {
                            "id": acc_id,
                            "name": cfg.get("name", f"Account {acc_id}"),
                            "currency": cfg.get("currency", "USD"),
                            "mode": cfg.get("mode", "STANDARD_PROP"),
                            "is_active": cfg.get("is_active", True),
                            "allowed_symbols": cfg.get("allowed_symbols", ["XAUUSD"]),
                            "symbol_lots": cfg.get("symbol_lots", {}),
                            "max_lot_size": cfg.get("max_lot_size", 0.05),
                            "max_open_trades": cfg.get("max_open_trades", 1),
                            "daily_profit_target": cfg.get("daily_profit_target", 100.0),
                            "daily_max_loss": cfg.get("daily_max_loss", 50.0),
                            "connected": True
                        }
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(accounts).encode('utf-8'))
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                return

            else:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Not found")
                return

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def main():
    """Start the dashboard server"""
    print("=" * 85)
    print("   🌐 AI TRADING SYSTEM - REAL-TIME DASHBOARD UI")
    print(f"   📊 Access Dashboard: http://localhost:{PORT}")
    print(f"   🤖 API Status: http://localhost:{PORT}/api/status")
    print(f"   📈 API Trades: http://localhost:{PORT}/api/trades")
    print(f"   💾 API Accounts: http://localhost:{PORT}/api/accounts")
    print("=" * 85)
    print()
    print("[DASHBOARD] Starting AI Trading Dashboard server...")
    print(f"[DASHBOARD] Listening on http://localhost:{PORT}")
    print("[DASHBOARD] Open this URL in your web browser to monitor AI agents in real-time")
    print("[DASHBOARD] Press Ctrl+C to stop the dashboard")
    print()

    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[DASHBOARD] Shutting down dashboard server...")


if __name__ == "__main__":
    main()
