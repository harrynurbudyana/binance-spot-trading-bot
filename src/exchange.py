"""
Modul Client Bursa Binance Spot Testnet.
Menangani koneksi, otentikasi, pembacaan saldo, dan eksekusi order menggunakan library ccxt.
"""

import logging
from typing import Dict, Any, Optional
import ccxt
from src.config import BotConfig

logger = logging.getLogger("ExchangeClient")


class BinanceExchangeClient:
    """Wrapper client bursa Binance Spot menggunakan CCXT."""

    def __init__(self, config: BotConfig):
        self.config = config
        self.exchange = self._init_exchange()

    def _init_exchange(self) -> ccxt.binance:
        """Inisialisasi instance ccxt.binance dengan konfigurasi testnet."""
        exchange_params: Dict[str, Any] = {
            "apiKey": self.config.api_key,
            "secret": self.config.secret_key,
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
                "adjustForTimeDifference": True,
                "recvWindow": 60000,
            },
        }

        exchange = ccxt.binance(exchange_params)

        if self.config.is_testnet:
            exchange.set_sandbox_mode(True)
            logger.info("Menggunakan Binance Spot Testnet (Sandbox Mode).")
        else:
            logger.warning("PERINGATAN: Menggunakan Binance Live / Production (Mainnet)!")

        return exchange

    def load_markets(self, reload: bool = False) -> Dict[str, Any]:
        """Memuat daftar pasangan mata uang dan aturan trading dari bursa."""
        return self.exchange.load_markets(reload)

    def get_market(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Mengambil metadata market untuk pasangan aset tertentu."""
        sym = symbol or self.config.symbol
        if not self.exchange.markets:
            self.load_markets()
        if sym not in self.exchange.markets:
            raise ValueError(f"Pasangan simbol '{sym}' tidak ditemukan di bursa Binance.")
        return self.exchange.markets[sym]

    def amount_to_precision(self, symbol: str, amount: float) -> float:
        """Menyesuaikan jumlah koin dengan tingkat presisi lot size Binance."""
        return float(self.exchange.amount_to_precision(symbol, amount))

    def price_to_precision(self, symbol: str, price: float) -> float:
        """Menyesuaikan harga dengan tingkat presisi tick size Binance."""
        return float(self.exchange.price_to_precision(symbol, price))

    def test_public_connection(self) -> Dict[str, Any]:
        """
        Menguji konektivitas publik ke bursa Binance Spot Testnet.
        Tidak memerlukan API Key.
        """
        try:
            server_time_ms = self.exchange.fetch_time()
            markets = self.load_markets()
            symbol_exists = self.config.symbol in markets

            return {
                "success": True,
                "server_time_ms": server_time_ms,
                "total_markets": len(markets),
                "symbol_supported": symbol_exists,
                "sandbox_urls": self.exchange.urls.get("test", {}),
            }
        except Exception as e:
            logger.error(f"Gagal menguji koneksi publik: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def test_private_connection(self) -> Dict[str, Any]:
        """
        Menguji kredensial API privat (membaca saldo).
        Memerlukan BINANCE_API_KEY dan BINANCE_SECRET_KEY yang valid.
        """
        if not self.config.has_valid_api_keys:
            return {
                "success": False,
                "error": "Kunci API masih berupa placeholder. Silakan atur BINANCE_API_KEY dan BINANCE_SECRET_KEY di file .env.",
            }

        try:
            balance = self.exchange.fetch_balance()
            # Ambil semua aset yang memiliki saldo > 0
            non_zero_balances = {}
            for asset, val in balance.get("total", {}).items():
                if val and float(val) > 0:
                    non_zero_balances[asset] = {
                        "free": balance.get("free", {}).get(asset, 0.0),
                        "used": balance.get("used", {}).get(asset, 0.0),
                        "total": val,
                    }

            return {
                "success": True,
                "non_zero_balances": non_zero_balances,
                "usdt_free": balance.get("free", {}).get("USDT", 0.0),
                "usdt_total": balance.get("total", {}).get("USDT", 0.0),
            }
        except ccxt.AuthenticationError as e:
            return {
                "success": False,
                "error": f"Autentikasi Gagal (Kunci API / Secret tidak valid): {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Gagal mengakses API privat: {e}",
            }

    def get_free_balance(self, asset: str = "USDT") -> float:
        """Mengambil saldo bebas (free balance) untuk aset tertentu."""
        try:
            balance = self.exchange.fetch_balance()
            free_amount = balance.get("free", {}).get(asset, 0.0)
            return float(free_amount or 0.0)
        except Exception as e:
            logger.error(f"Gagal mengambil saldo {asset}: {e}")
            return 0.0

    def create_market_buy_order(self, symbol: str, amount: float) -> Dict[str, Any]:
        """
        Mengeksekusi order Market Buy.
        Jika DRY_RUN aktif, hanya melakukan simulasi order.
        """
        adj_amount = self.amount_to_precision(symbol, amount)

        if self.config.dry_run:
            logger.info(f"[SIMULASI / DRY RUN] Market BUY order: {adj_amount} {symbol}")
            return {
                "id": "dry_run_buy_order",
                "symbol": symbol,
                "side": "buy",
                "type": "market",
                "amount": adj_amount,
                "status": "closed",
                "dry_run": True,
            }

        try:
            order = self.exchange.create_market_buy_order(symbol, adj_amount)
            logger.info(f"Order Market Buy Berhasil: ID={order.get('id')} Jumlah={adj_amount}")
            return order
        except ccxt.InsufficientFunds as e:
            logger.error(f"Saldo tidak cukup untuk Market Buy: {e}")
            raise
        except Exception as e:
            logger.error(f"Gagal mengeksekusi Market Buy: {e}")
            raise

    def create_market_sell_order(self, symbol: str, amount: float) -> Dict[str, Any]:
        """
        Mengeksekusi order Market Sell.
        Jika DRY_RUN aktif, hanya melakukan simulasi order.
        """
        adj_amount = self.amount_to_precision(symbol, amount)

        if self.config.dry_run:
            logger.info(f"[SIMULASI / DRY RUN] Market SELL order: {adj_amount} {symbol}")
            return {
                "id": "dry_run_sell_order",
                "symbol": symbol,
                "side": "sell",
                "type": "market",
                "amount": adj_amount,
                "status": "closed",
                "dry_run": True,
            }

        try:
            order = self.exchange.create_market_sell_order(symbol, adj_amount)
            logger.info(f"Order Market Sell Berhasil: ID={order.get('id')} Jumlah={adj_amount}")
            return order
        except Exception as e:
            logger.error(f"Gagal mengeksekusi Market Sell: {e}")
            raise
