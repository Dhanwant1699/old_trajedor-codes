import unittest
import os
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import CONFIG
from core.dual_account_manager import DualAccountManager, AccountProfile
from core.dashboard_server import (
    get_admin_config,
    save_admin_config,
    disconnect_account_in_config,
    reconnect_account_in_config,
    delete_archived_account_in_config,
    delete_account_in_config
)


class TestMultiAssetAccountManagement(unittest.TestCase):

    def setUp(self):
        self.mgr = DualAccountManager()

    def test_config_symbols(self):
        """Verify global config has both XAUUSD and BTCUSD."""
        self.assertIn("XAUUSD", CONFIG.SYMBOLS)
        self.assertIn("BTCUSD", CONFIG.SYMBOLS)

    def test_vantage_markets_bitcoin_enabled(self):
        """Verify Vantage Markets (acc_3) is configured for both Gold and Bitcoin."""
        profiles = self.mgr.profiles
        self.assertIn("acc_3", profiles)
        acc3 = profiles["acc_3"]
        
        # Verify allowed symbols
        self.assertTrue(acc3.is_symbol_allowed("XAUUSD"))
        self.assertTrue(acc3.is_symbol_allowed("BTCUSD"))
        self.assertTrue(acc3.is_symbol_allowed("BTCUSD+"))
        
        # Verify per-symbol lots
        self.assertEqual(acc3.get_lot_size_for_symbol("XAUUSD"), 0.3)
        self.assertGreater(acc3.get_lot_size_for_symbol("BTCUSD"), 0.0)

    def test_gold_only_accounts(self):
        """Verify accounts with Gold only reject Bitcoin trades."""
        profiles = self.mgr.profiles
        if "acc_1" in profiles:
            acc1 = profiles["acc_1"]
            self.assertTrue(acc1.is_symbol_allowed("XAUUSD"))
            self.assertFalse(acc1.is_symbol_allowed("BTCUSD"))

        if "acc_2" in profiles:
            acc2 = profiles["acc_2"]
            self.assertTrue(acc2.is_symbol_allowed("XAUUSD"))
            self.assertFalse(acc2.is_symbol_allowed("BTCUSD"))

    def test_admin_config_save_and_reload(self):
        """Verify admin config accurately persists allowed_symbols, symbol_lots, and symbol_settings."""
        cfg = get_admin_config()
        self.assertIn("acc_3", cfg.get("accounts", {}))
        acc3_cfg = cfg["accounts"]["acc_3"]
        self.assertIn("BTCUSD", acc3_cfg.get("allowed_symbols", []))
        self.assertIn("BTCUSD", acc3_cfg.get("symbol_lots", {}))

        # Verify symbol_settings structure
        self.assertIn("symbol_settings", acc3_cfg)
        xau_set = acc3_cfg["symbol_settings"]["XAUUSD"]
        btc_set = acc3_cfg["symbol_settings"]["BTCUSD"]
        self.assertEqual(xau_set["max_lot_size"], 0.3)
        self.assertIn("max_open_positions", xau_set)
        self.assertIn("max_lot_size", btc_set)
        self.assertIn("max_open_positions", btc_set)

    def test_symbol_specific_methods(self):
        """Verify AccountProfile helper methods correctly extract symbol-specific limits."""
        profile = AccountProfile(
            account_id="acc_test",
            name="Test Account",
            terminal_path="C:\\fake\\terminal64.exe",
            currency="USD",
            magic_number=777888,
            mode="STANDARD_PROP",
            is_active=True,
            allowed_symbols=["XAUUSD", "BTCUSD"],
            symbol_settings={
                "XAUUSD": {
                    "max_lot_size": 0.20,
                    "max_open_positions": 3,
                    "daily_profit_target": 1200.0,
                    "daily_max_loss": 600.0
                },
                "BTCUSD": {
                    "max_lot_size": 0.03,
                    "max_open_positions": 1,
                    "daily_profit_target": 400.0,
                    "daily_max_loss": 200.0
                }
            }
        )
        
        # XAUUSD assertions
        self.assertEqual(profile.get_lot_size_for_symbol("XAUUSD"), 0.20)
        self.assertEqual(profile.get_max_positions_for_symbol("XAUUSD"), 3)
        self.assertEqual(profile.get_daily_target_for_symbol("XAUUSD"), 1200.0)
        self.assertEqual(profile.get_daily_loss_for_symbol("XAUUSD"), 600.0)
        
        # BTCUSD assertions
        self.assertEqual(profile.get_lot_size_for_symbol("BTCUSD"), 0.03)
        self.assertEqual(profile.get_max_positions_for_symbol("BTCUSD"), 1)
        self.assertEqual(profile.get_daily_target_for_symbol("BTCUSD"), 400.0)
        self.assertEqual(profile.get_daily_loss_for_symbol("BTCUSD"), 200.0)

    def test_symbol_settings_fallback(self):
        """Verify fallback behavior when symbol_settings is not provided."""
        profile = AccountProfile(
            account_id="acc_fallback",
            name="Fallback Account",
            terminal_path="C:\\fake\\terminal64.exe",
            currency="USD",
            magic_number=777888,
            mode="STANDARD_PROP",
            max_lot_size=0.08,
            max_open_trades=2,
            daily_profit_target=300.0,
            daily_max_loss=150.0,
            symbol_lots={
                "XAUUSD": 0.08,
                "BTCUSD": 0.02
            }
        )
        self.assertEqual(profile.get_lot_size_for_symbol("XAUUSD"), 0.08)
        self.assertEqual(profile.get_lot_size_for_symbol("BTCUSD"), 0.02)
        self.assertEqual(profile.get_max_positions_for_symbol("XAUUSD"), 2)
        self.assertEqual(profile.get_max_positions_for_symbol("BTCUSD"), 2)
        self.assertEqual(profile.get_daily_target_for_symbol("XAUUSD"), 300.0)
        self.assertEqual(profile.get_daily_loss_for_symbol("XAUUSD"), 150.0)

    def test_delete_account_in_config(self):
        """Verify delete_account_in_config permanently removes an active account."""
        cfg = get_admin_config()
        test_acc_id = "acc_test_delete"
        cfg["accounts"][test_acc_id] = {
            "id": test_acc_id,
            "name": "Temporary Test Account",
            "terminal_path": "C:\\fake\\path",
            "is_active": True
        }
        save_admin_config(cfg)

        # Verify added
        cfg_after = get_admin_config()
        self.assertIn(test_acc_id, cfg_after["accounts"])

        # Perform permanent delete
        ok, msg = delete_account_in_config(test_acc_id)
        self.assertTrue(ok)
        self.assertIn("permanently deleted", msg)

        # Verify removed
        cfg_final = get_admin_config()
        self.assertNotIn(test_acc_id, cfg_final["accounts"])

    def test_disconnect_and_reconnect_account(self):
        """Verify disconnecting an account archives it, and reconnecting restores it."""
        cfg = get_admin_config()
        test_acc_id = "acc_test_arch"
        cfg["accounts"][test_acc_id] = {
            "id": test_acc_id,
            "name": "Archive Test Account",
            "terminal_path": "C:\\fake\\path",
            "is_active": True
        }
        save_admin_config(cfg)

        # Disconnect
        ok_disc, msg_disc = disconnect_account_in_config(test_acc_id)
        self.assertTrue(ok_disc)
        cfg_arch = get_admin_config()
        self.assertNotIn(test_acc_id, cfg_arch["accounts"])
        self.assertIn(test_acc_id, cfg_arch["archived_accounts"])

        # Reconnect
        ok_rec, msg_rec = reconnect_account_in_config(test_acc_id)
        self.assertTrue(ok_rec)
        cfg_rec = get_admin_config()
        self.assertIn(test_acc_id, cfg_rec["accounts"])
        self.assertNotIn(test_acc_id, cfg_rec["archived_accounts"])

        # Clean up
        delete_account_in_config(test_acc_id)


if __name__ == "__main__":
    unittest.main()
