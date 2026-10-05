"""
Modul Konfigurasi Bot Trading Binance Spot Testnet.
Membaca environment variables dari .env dan menyediakan objek konfigurasi yang terstruktur.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Cari path file .env dari direktori root proyek
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Muat file .env jika ada
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=True)
else:
    load_dotenv(override=True)


@dataclass
class BotConfig:
    """Struktur data konfigurasi untuk bot trading."""
    api_key: str
    secret_key: str
    symbol: str
    timeframe: str
    rsi_period: int
    rsi_oversold: float
    rsi_overbought: float
    max_balance_risk_percent: float
    stop_loss_percent: float
    poll_interval_seconds: int
    is_testnet: bool
    dry_run: bool
    strategy_type: str = "HYBRID"
    ai_confidence_threshold: float = 0.35
    take_profit_percent: float = 1.2
    watchlist: Optional[list] = None

    @property
    def symbols_to_scan(self) -> list:
        """Daftar koin yang dipantau (mendukung scanner multi-market)."""
        if self.watchlist and len(self.watchlist) > 0:
            return self.watchlist
        return [self.symbol]

    @property
    def has_valid_api_keys(self) -> bool:
        """Memeriksa apakah API Key bukan nilai default placeholder."""
        placeholders = [
            "",
            "your_binance_testnet_api_key_here",
            "your_api_key_here",
        ]
        return (
            bool(self.api_key)
            and bool(self.secret_key)
            and self.api_key.strip() not in placeholders
            and self.secret_key.strip() not in placeholders
        )

    def print_summary(self):
        """Menampilkan ringkasan konfigurasi aktif."""
        print("=" * 60)
        print("          KONFIGURASI BOT TRADING SPOT TESTNET")
        print("=" * 60)
        if len(self.symbols_to_scan) > 1:
            print(f" Mode Market Scanner  : AKTIF ({len(self.symbols_to_scan)} Pasangan Kripto)")
            print(f" Watchlist Scanner    : {', '.join(self.symbols_to_scan)}")
        else:
            print(f" Pasangan Aset        : {self.symbol}")
        print(f" Timeframe            : {self.timeframe}")
        print(f" Tipe Strategi        : {self.strategy_type.upper()}")
        print(f" Indikator            : RSI (Periode: {self.rsi_period})")
        print(f" Sinyal Beli (Oversold): RSI < {self.rsi_oversold}")
        print(f" Sinyal Jual (Overbought): RSI > {self.rsi_overbought}")
        print(f" Batas Risiko Beli    : Maks {self.max_balance_risk_percent}% Saldo USDT")
        print(f" Target Take Profit   : +{self.take_profit_percent}% di atas harga entry")
        print(f" Stop Loss Statis     : -{self.stop_loss_percent}% di bawah harga entry")
        print(f" Interval Polling     : {self.poll_interval_seconds} detik")
        print(f" Mode Testnet         : {'AKTIF' if self.is_testnet else 'NON-AKTIF (MAINNET)'}")
        print(f" Mode Dry Run         : {'AKTIF (Simulasi)' if self.dry_run else 'NON-AKTIF (Order Nyata)'}")
        print(f" Status Kunci API     : {'Terisi' if self.has_valid_api_keys else 'Placeholder (Belum Diatur)'}")
        print("=" * 60)


def load_config() -> BotConfig:
    """Memuat dan memvalidasi konfigurasi dari environment variables."""
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    secret_key = os.getenv("BINANCE_SECRET_KEY", "").strip()

    symbol = os.getenv("SYMBOL", "BTC/USDT").strip().upper()
    watchlist_env = os.getenv("WATCHLIST", os.getenv("SYMBOLS", "")).strip()
    if watchlist_env:
        watchlist = [s.strip().upper() for s in watchlist_env.split(",") if s.strip()]
    else:
        watchlist = [symbol]

    timeframe = os.getenv("TIMEFRAME", "15m").strip().lower()

    strategy_type = os.getenv("STRATEGY_TYPE", "HYBRID").strip().upper()
    try:
        ai_confidence_threshold = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.35"))
    except ValueError:
        ai_confidence_threshold = 0.35

    try:
        rsi_period = int(os.getenv("RSI_PERIOD", "14"))
    except ValueError:
        rsi_period = 14

    try:
        rsi_oversold = float(os.getenv("RSI_OVERSOLD", "30.0"))
    except ValueError:
        rsi_oversold = 30.0

    try:
        rsi_overbought = float(os.getenv("RSI_OVERBOUGHT", "70.0"))
    except ValueError:
        rsi_overbought = 70.0

    try:
        max_balance_risk_percent = float(os.getenv("MAX_BALANCE_RISK_PERCENT", "10.0"))
    except ValueError:
        max_balance_risk_percent = 10.0

    try:
        stop_loss_percent = float(os.getenv("STOP_LOSS_PERCENT", "2.0"))
    except ValueError:
        stop_loss_percent = 2.0

    try:
        take_profit_percent = float(os.getenv("TAKE_PROFIT_PERCENT", "1.2"))
    except ValueError:
        take_profit_percent = 1.2

    try:
        poll_interval_seconds = int(os.getenv("POLL_INTERVAL_SECONDS", "15"))
    except ValueError:
        poll_interval_seconds = 15

    is_testnet = os.getenv("IS_TESTNET", "True").lower() in ("true", "1", "yes", "y")
    dry_run = os.getenv("DRY_RUN", "True").lower() in ("true", "1", "yes", "y")

    return BotConfig(
        api_key=api_key,
        secret_key=secret_key,
        symbol=symbol,
        timeframe=timeframe,
        rsi_period=rsi_period,
        rsi_oversold=rsi_oversold,
        rsi_overbought=rsi_overbought,
        max_balance_risk_percent=max_balance_risk_percent,
        stop_loss_percent=stop_loss_percent,
        poll_interval_seconds=poll_interval_seconds,
        is_testnet=is_testnet,
        dry_run=dry_run,
        strategy_type=strategy_type,
        ai_confidence_threshold=ai_confidence_threshold,
        take_profit_percent=take_profit_percent,
        watchlist=watchlist,
    )
