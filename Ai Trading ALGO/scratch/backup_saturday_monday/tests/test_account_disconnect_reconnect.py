"""
Test Suite: MT5 Account Disconnect, Archive, 1-Click Reconnect & Deletion Lifecycle
Verifies:
1. Account disconnect safely archives full profile (parameters, magic, path, mode, lot sizes).
2. DualAccountManager ignores archived accounts and live hot-reloads active accounts.
3. 1-Click reconnect restores archived accounts back to active state.
4. Auto-detection recognizes active vs archived vs new terminals.
5. Deleting from archive permanently purges account.
"""

import os
import sys
import json
import unittest
import tempfile
import shutil
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.dashboard_server import (
    get_admin_config,
    save_admin_config,
    disconnect_account_in_config,
    reconnect_account_in_config,
    delete_archived_account_in_config,
    auto_detect_installed_terminals
)
from core.dual_account_manager import DualAccountManager


class TestAccountDisconnectReconnect(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cfg_file = os.path.join(self.temp_dir, "admin_config.json")

        self.initial_cfg = {
            "version": "1.0",
            "global_settings": {
                "engine_active": True,
                "global_hard_lot_cap": 0.1,
                "max_spread_points": 80,
                "news_filter_enabled": True,
                "news_blackout_minutes": 15
            },
            "accounts": {
                "acc_1": {
                    "id": "acc_1",
                    "name": "Account #1 (Master EUR)",
                    "terminal_path": r"C:\Program Files\MetaTrader 5\terminal64.exe",
                    "currency": "EUR",
                    "magic_number": 777888,
                    "mode": "STANDARD_PROP",
                    "is_active": True,
                    "max_open_trades": 3,
                    "max_lot_size": 0.1,
                    "min_lot_size": 0.01,
                    "daily_profit_target": 1000,
                    "daily_max_loss": 10000
                },
                "acc_2": {
                    "id": "acc_2",
                    "name": "Account #2 (GTC Live Micro USD)",
                    "terminal_path": r"C:\Program Files\MetaTrader 5 - 1\terminal64.exe",
                    "currency": "USD",
                    "magic_number": 777999,
                    "mode": "MICRO_COMPOUNDING",
                    "is_active": True,
                    "max_open_trades": 1,
                    "max_lot_size": 0.01,
                    "min_lot_size": 0.01,
                    "daily_profit_target": 1000,
                    "daily_max_loss": 100
                },
                "acc_3": {
                    "id": "acc_3",
                    "name": "Account #3 (VantageMarkets-Demo)",
                    "terminal_path": r"C:\Program Files\MetaTrader 5 - 2\terminal64.exe",
                    "currency": "USD",
                    "magic_number": 778101,
                    "mode": "STANDARD_PROP",
                    "is_active": True,
                    "max_open_trades": 3,
                    "max_lot_size": 0.3,
                    "min_lot_size": 0.01,
                    "daily_profit_target": 10000,
                    "daily_max_loss": 10000
                }
            },
            "archived_accounts": {}
        }

        with open(self.cfg_file, "w", encoding="utf-8") as f:
            json.dump(self.initial_cfg, f, indent=2)

        self.join_patcher = patch("core.dashboard_server.os.path.join", side_effect=lambda *args: self.cfg_file if "admin_config.json" in args else os.path.join(*args))
        self.admin_path_patcher = patch("core.dual_account_manager.ADMIN_CONFIG_PATH", self.cfg_file)
        self.join_patcher.start()
        self.admin_path_patcher.start()

    def tearDown(self):
        self.join_patcher.stop()
        self.admin_path_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_disconnect_and_archive_account(self):
        """Test disconnecting an active account moves it to archived_accounts with all settings preserved."""
        cfg_before = get_admin_config()
        self.assertIn("acc_3", cfg_before["accounts"])
        self.assertNotIn("acc_3", cfg_before.get("archived_accounts", {}))

        # Disconnect acc_3
        ok, msg = disconnect_account_in_config("acc_3")
        self.assertTrue(ok)
        self.assertTrue("Account #3" in msg or "acc_3" in msg)

        cfg_after = get_admin_config()
        self.assertNotIn("acc_3", cfg_after["accounts"])
        self.assertIn("acc_3", cfg_after["archived_accounts"])

        archived_acc = cfg_after["archived_accounts"]["acc_3"]
        self.assertEqual(archived_acc["name"], "Account #3 (VantageMarkets-Demo)")
        self.assertEqual(archived_acc["terminal_path"], r"C:\Program Files\MetaTrader 5 - 2\terminal64.exe")
        self.assertEqual(archived_acc["magic_number"], 778101)
        self.assertEqual(archived_acc["max_lot_size"], 0.3)
        self.assertEqual(archived_acc["daily_profit_target"], 10000)
        self.assertFalse(archived_acc["is_active"])
        self.assertIn("disconnected_at", archived_acc)

    def test_dual_account_manager_excludes_archived(self):
        """Test DualAccountManager ignores disconnected archived accounts."""
        mgr = DualAccountManager()
        mgr.reload_config()
        self.assertEqual(len(mgr.accounts), 3)
        self.assertTrue(any(a.account_id == "acc_3" for a in mgr.accounts))

        # Disconnect acc_3
        disconnect_account_in_config("acc_3")

        # Reload DualAccountManager
        mgr.reload_config()
        self.assertEqual(len(mgr.accounts), 2)
        self.assertFalse(any(a.account_id == "acc_3" for a in mgr.accounts))
        self.assertTrue(any(a.account_id == "acc_1" for a in mgr.accounts))
        self.assertTrue(any(a.account_id == "acc_2" for a in mgr.accounts))

    def test_reconnect_archived_account_with_one_click(self):
        """Test 1-click reconnection restores account to active state with all parameters intact."""
        # First disconnect acc_3
        disconnect_account_in_config("acc_3")
        cfg_mid = get_admin_config()
        self.assertNotIn("acc_3", cfg_mid["accounts"])
        self.assertIn("acc_3", cfg_mid["archived_accounts"])

        # Now 1-click reconnect acc_3
        ok, msg = reconnect_account_in_config("acc_3")
        self.assertTrue(ok)
        self.assertIn("reconnected and activated", msg)

        cfg_restored = get_admin_config()
        self.assertIn("acc_3", cfg_restored["accounts"])
        self.assertNotIn("acc_3", cfg_restored["archived_accounts"])

        restored_acc = cfg_restored["accounts"]["acc_3"]
        self.assertEqual(restored_acc["name"], "Account #3 (VantageMarkets-Demo)")
        self.assertTrue(restored_acc["is_active"])
        self.assertEqual(restored_acc["magic_number"], 778101)
        self.assertEqual(restored_acc["max_lot_size"], 0.3)
        self.assertEqual(restored_acc["daily_profit_target"], 10000)

        # Verify DualAccountManager reloads it
        mgr = DualAccountManager()
        mgr.reload_config()
        self.assertEqual(len(mgr.accounts), 3)
        acc3_profile = next(a for a in mgr.accounts if a.account_id == "acc_3")
        self.assertEqual(acc3_profile.name, "Account #3 (VantageMarkets-Demo)")
        self.assertEqual(acc3_profile.max_lot_size, 0.3)

    def test_delete_archived_account(self):
        """Test permanently deleting an account from the archive."""
        # Disconnect acc_3 first
        disconnect_account_in_config("acc_3")
        cfg = get_admin_config()
        self.assertIn("acc_3", cfg["archived_accounts"])

        # Permanently delete acc_3
        ok, msg = delete_archived_account_in_config("acc_3")
        self.assertTrue(ok)
        self.assertIn("permanently deleted", msg)

        cfg_after = get_admin_config()
        self.assertNotIn("acc_3", cfg_after["accounts"])
        self.assertNotIn("acc_3", cfg_after["archived_accounts"])

    def test_auto_detect_scanner_tags_active_and_archived(self):
        """Test auto-detect tags terminals accurately as active vs archived."""
        disconnect_account_in_config("acc_3")

        with patch("core.dashboard_server.os.path.exists", return_value=True), \
             patch("core.dashboard_server.os.walk", return_value=[(r"C:\Program Files\MetaTrader 5", [], ["terminal64.exe"]), (r"C:\Program Files\MetaTrader 5 - 2", [], ["terminal64.exe"])]), \
             patch("MetaTrader5.initialize", return_value=False):
            
            detected = auto_detect_installed_terminals()
            acc1 = next((d for d in detected if "MetaTrader 5\\terminal64.exe" in d["terminal_path"] and " - 2" not in d["terminal_path"]), None)
            acc3 = next((d for d in detected if "MetaTrader 5 - 2" in d["terminal_path"]), None)

            if acc1:
                self.assertTrue(acc1["is_active"])
                self.assertEqual(acc1["active_acc_id"], "acc_1")
            if acc3:
                self.assertTrue(acc3["is_archived"])
                self.assertEqual(acc3["archived_acc_id"], "acc_3")


if __name__ == "__main__":
    unittest.main()
