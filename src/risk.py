"""
Modul Manajemen Risiko (Risk Management).
Menangani:
1. Pembatasan modal pembelian maksimal 10% dari saldo USDT yang tersedia.
2. Perhitungan dan pemantauan Stop Loss statis 2% di bawah harga entry.
3. Validasi aturan ukuran minimum (lot size & notional value) dari bursa Binance.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from src.config import BotConfig
from src.exchange import BinanceExchangeClient

logger = logging.getLogger("RiskManager")


@dataclass
class Position:
    """Representasi posisi trading aktif."""
    symbol: str
    entry_price: float
    amount: float
    stop_loss_price: float
    entry_time: str
    take_profit_price: float = 0.0
    order_id: Optional[str] = None

    def calculate_pnl(self, current_price: float) -> Tuple[float, float]:
        """
        Menghitung PnL (Profit & Loss).
        Return: (pnl_usdt, pnl_percent)
        """
        pnl_usdt = (current_price - self.entry_price) * self.amount
        pnl_percent = ((current_price - self.entry_price) / self.entry_price) * 100.0
        return pnl_usdt, pnl_percent


class RiskManager:
    """Pengelola risiko transaksi dan pelindung modal."""

    def __init__(self, config: BotConfig, exchange_client: BinanceExchangeClient):
        self.config = config
        self.client = exchange_client
        self.max_risk_pct = config.max_balance_risk_percent  # Default: 10.0%
        self.stop_loss_pct = config.stop_loss_percent        # Default: 1.0% - 2.0%
        self.take_profit_pct = getattr(config, "take_profit_percent", 1.2)  # Default: 1.2%

    def calculate_position_size(
        self,
        symbol: str,
        current_price: float,
        simulated_balance: Optional[float] = None,
    ) -> Tuple[bool, float, str]:
        """
        Menghitung jumlah koin yang dibeli berdasarkan aturan maksimal 10% saldo USDT.

        Return:
            (is_valid: bool, amount: float, message: str)
        """
        if current_price <= 0:
            return False, 0.0, "Harga terkini tidak valid (<= 0)."

        # Ambil saldo USDT bebas dari bursa atau gunakan saldo simulasi jika dry-run tanpa saldo
        if simulated_balance is not None:
            free_usdt = simulated_balance
        else:
            free_usdt = self.client.get_free_balance(asset="USDT")

        # Jika saldo kosong di dry run, berikan saldo simulasi 1000 USDT agar testing tetap berjalan mulus
        if free_usdt <= 0 and self.config.dry_run:
            free_usdt = 1000.0
            logger.info("Saldo USDT kosong, menggunakan saldo simulasi 1000.0 USDT untuk pengujian Dry Run.")

        if free_usdt <= 0:
            return False, 0.0, f"Saldo USDT tidak mencukupi (Tersedia: {free_usdt} USDT)."

        # Alokasikan maksimal 10% dari saldo USDT yang tersedia
        allocated_usdt = free_usdt * (self.max_risk_pct / 100.0)

        # Ambil aturan batas minimum dari bursa
        market = self.client.get_market(symbol)
        limits = market.get("limits", {})
        min_cost = limits.get("cost", {}).get("min") or 5.0  # Binance min notional biasanya 5 atau 10 USDT
        min_amount = limits.get("amount", {}).get("min") or 0.0001

        if allocated_usdt < min_cost:
            return (
                False,
                0.0,
                f"Alokasi dana {allocated_usdt:.2f} USDT (10% dari {free_usdt:.2f} USDT) "
                f"berada di bawah batas minimum notional bursa ({min_cost:.2f} USDT).",
            )

        # Hitung jumlah koin yang akan dibeli
        raw_amount = allocated_usdt / current_price

        # Sesuaikan dengan tingkat presisi lot size Binance
        adj_amount = self.client.amount_to_precision(symbol, raw_amount)

        if adj_amount < min_amount:
            return (
                False,
                0.0,
                f"Jumlah pembelian {adj_amount} {symbol} kurang dari minimum lot size bursa ({min_amount}).",
            )

        msg = (
            f"Alokasi modal valid: {allocated_usdt:.2f} USDT ({self.max_risk_pct}% dari {free_usdt:.2f} USDT) "
            f"-> {adj_amount} {symbol} pada harga {current_price:.2f} USDT."
        )
        return True, adj_amount, msg

    def calculate_stop_loss_price(self, symbol: str, entry_price: float) -> float:
        """
        Menghitung harga Stop Loss statis 2% di bawah harga beli (entry).
        Rumus: stop_loss_price = entry_price * (1 - 0.02)
        """
        sl_multiplier = 1.0 - (self.stop_loss_pct / 100.0)
        raw_sl_price = entry_price * sl_multiplier
        return self.client.price_to_precision(symbol, raw_sl_price)

    def is_stop_loss_triggered(self, position: Position, current_price: float) -> bool:
        """
        Memeriksa apakah harga saat ini telah menyentuh atau menembus level Stop Loss statis.
        """
        return current_price <= position.stop_loss_price

    def calculate_take_profit_price(self, symbol: str, entry_price: float) -> float:
        """
        Menghitung harga target Take Profit (misal +1.2%) di atas harga beli (entry).
        Rumus: take_profit_price = entry_price * (1 + (take_profit_pct / 100))
        """
        tp_multiplier = 1.0 + (self.take_profit_pct / 100.0)
        raw_tp_price = entry_price * tp_multiplier
        return self.client.price_to_precision(symbol, raw_tp_price)

    def is_take_profit_triggered(self, position: Position, current_price: float) -> bool:
        """
        Memeriksa apakah harga saat ini telah mencapai target Take Profit.
        """
        if position.take_profit_price and position.take_profit_price > 0:
            return current_price >= position.take_profit_price
        return False
