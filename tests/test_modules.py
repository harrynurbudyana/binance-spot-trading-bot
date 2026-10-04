"""
Unit Test untuk Modul-Modul Bot Trading (Config, Strategy, Risk).
Memastikan logika matematika RSI dan manajemen risiko 10% & Stop Loss 2% bekerja secara presisi.
"""

import unittest
import pandas as pd
import numpy as np

from src.config import BotConfig
from src.strategy import RSIStrategy, SignalAction
from src.risk import Position, RiskManager


class MockExchangeClient:
    """Mock client untuk menguji logika bisnis tanpa request jaringan."""

    def __init__(self, config):
        self.config = config

    def get_market(self, symbol):
        return {
            "symbol": symbol,
            "limits": {
                "amount": {"min": 0.0001, "max": 1000.0},
                "cost": {"min": 5.0, "max": 100000.0},
            },
            "precision": {
                "amount": 0.00001,
                "price": 0.01,
            },
        }

    def amount_to_precision(self, symbol, amount):
        return round(float(amount), 5)

    def price_to_precision(self, symbol, price):
        return round(float(price), 2)

    def get_free_balance(self, asset="USDT"):
        return 1000.0


class TestTradingBotModules(unittest.TestCase):
    def setUp(self):
        self.config = BotConfig(
            api_key="test_key",
            secret_key="test_secret",
            symbol="BTC/USDT",
            timeframe="15m",
            rsi_period=14,
            rsi_oversold=30.0,
            rsi_overbought=70.0,
            max_balance_risk_percent=10.0,
            stop_loss_percent=2.0,
            poll_interval_seconds=15,
            is_testnet=True,
            dry_run=True,
        )
        self.mock_client = MockExchangeClient(self.config)
        self.risk_manager = RiskManager(self.config, self.mock_client)
        self.strategy = RSIStrategy(self.config)

    def test_rsi_calculation_and_signals(self):
        # 1. Buat data harga turun drastis berturut-turut untuk memicu oversold (RSI < 30)
        prices_down = [100.0 - i * 3.0 for i in range(25)]
        df_down = pd.DataFrame({"close": prices_down})
        signal_buy = self.strategy.evaluate(df_down)

        self.assertLess(signal_buy.rsi, 30.0)
        self.assertEqual(signal_buy.action, SignalAction.BUY)
        self.assertIn("Sinyal BELI", signal_buy.reason)

        # 2. Buat data harga naik konsisten untuk memicu overbought (RSI > 70)
        prices_up = [50.0 + i * 4.0 for i in range(25)]
        df_up = pd.DataFrame({"close": prices_up})
        signal_sell = self.strategy.evaluate(df_up)

        self.assertGreater(signal_sell.rsi, 70.0)
        self.assertEqual(signal_sell.action, SignalAction.SELL)
        self.assertIn("Sinyal JUAL", signal_sell.reason)

    def test_risk_management_10_percent_allocation(self):
        # Saldo USDT = 1000.0, Batas risiko = 10% -> Alokasi modal = 100.0 USDT
        current_price = 50000.0
        is_valid, amount, msg = self.risk_manager.calculate_position_size(
            symbol="BTC/USDT",
            current_price=current_price,
            simulated_balance=1000.0,
        )

        self.assertTrue(is_valid)
        expected_amount = round(100.0 / current_price, 5)  # 0.002 BTC
        self.assertEqual(amount, expected_amount)
        self.assertIn("100.00 USDT", msg)

    def test_risk_management_insufficient_balance(self):
        # Saldo sangat kecil, 10% bernilai < min notional 5 USDT -> Harus ditolak
        is_valid, amount, msg = self.risk_manager.calculate_position_size(
            symbol="BTC/USDT",
            current_price=50000.0,
            simulated_balance=20.0,  # 10% = 2.0 USDT < 5.0 USDT min cost
        )
        self.assertFalse(is_valid)
        self.assertEqual(amount, 0.0)
        self.assertIn("di bawah batas minimum notional", msg)

    def test_static_stop_loss_2_percent(self):
        entry_price = 100.0
        sl_price = self.risk_manager.calculate_stop_loss_price("BTC/USDT", entry_price)

        # Stop loss 2% di bawah 100 adalah 98.0
        self.assertEqual(sl_price, 98.0)

        pos = Position(
            symbol="BTC/USDT",
            entry_price=entry_price,
            amount=1.0,
            stop_loss_price=sl_price,
            entry_time="2026-10-04 12:00:00",
        )

        # Jika harga masih 98.5 -> Stop loss belum terpicu
        self.assertFalse(self.risk_manager.is_stop_loss_triggered(pos, 98.5))

        # Jika harga turun ke 98.0 atau 97.9 -> Stop loss terpicu
        self.assertTrue(self.risk_manager.is_stop_loss_triggered(pos, 98.0))
        self.assertTrue(self.risk_manager.is_stop_loss_triggered(pos, 97.5))

        # PnL saat SL
        pnl_usdt, pnl_pct = pos.calculate_pnl(98.0)
        self.assertAlmostEqual(pnl_pct, -2.0, places=2)
        self.assertAlmostEqual(pnl_usdt, -2.0, places=2)

    def test_ai_feature_extraction_and_inference(self):
        from src.features import extract_features
        from src.ai_strategy import AIPredictiveStrategy

        # Buat dummy OHLCV 60 lilin
        dates = pd.date_range("2026-01-01", periods=60, freq="15min")
        dummy_df = pd.DataFrame({
            "timestamp": [int(d.timestamp() * 1000) for d in dates],
            "open": [100.0 + i * 0.1 for i in range(60)],
            "high": [101.0 + i * 0.1 for i in range(60)],
            "low": [99.0 + i * 0.1 for i in range(60)],
            "close": [100.5 + i * 0.1 for i in range(60)],
            "volume": [10.0 + (i % 5) for i in range(60)],
        })

        df_feat, feature_cols = extract_features(dummy_df)
        self.assertGreater(len(feature_cols), 10)
        self.assertIn("rsi_14", feature_cols)
        self.assertIn("volume_ratio", feature_cols)
        self.assertIn("atr_norm", feature_cols)

        # Uji inisialisasi AI Strategy
        ai_strat = AIPredictiveStrategy(self.config)
        signal = ai_strat.evaluate(dummy_df)
        self.assertIsNotNone(signal.action)
        self.assertIsNotNone(signal.rsi)


if __name__ == "__main__":
    unittest.main()
