"""
Modul Pembaca Harga (Market Data Fetcher).
Bertanggung jawab untuk mengambil data ticker, harga terkini, dan candlestick (OHLCV) dari bursa.
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from src.exchange import BinanceExchangeClient

logger = logging.getLogger("PriceFetcher")


class PriceFetcher:
    """Fetcher untuk data pasar publik dari Binance Spot Testnet."""

    def __init__(self, exchange_client: BinanceExchangeClient):
        self.client = exchange_client

    def get_ticker(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Mengambil data ticker terkini untuk pasangan aset."""
        sym = symbol or self.client.config.symbol
        try:
            ticker = self.client.exchange.fetch_ticker(sym)
            return {
                "symbol": sym,
                "last": float(ticker.get("last") or 0.0),
                "bid": float(ticker.get("bid") or 0.0),
                "ask": float(ticker.get("ask") or 0.0),
                "high": float(ticker.get("high") or 0.0),
                "low": float(ticker.get("low") or 0.0),
                "volume": float(ticker.get("baseVolume") or 0.0),
                "percentage": float(ticker.get("percentage") or 0.0),
                "timestamp": ticker.get("timestamp"),
            }
        except Exception as e:
            logger.error(f"Gagal mengambil ticker untuk {sym}: {e}")
            raise

    def get_latest_price(self, symbol: Optional[str] = None) -> float:
        """Mengambil harga transaksi terakhir (last price)."""
        ticker = self.get_ticker(symbol)
        return ticker["last"]

    def get_ohlcv_dataframe(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Mengambil data candlestick (OHLCV) dan mengonversinya menjadi pandas DataFrame.
        Columns: ['timestamp', 'datetime', 'open', 'high', 'low', 'close', 'volume']
        """
        sym = symbol or self.client.config.symbol
        tf = timeframe or self.client.config.timeframe

        try:
            raw_candles: List[List[Any]] = self.client.exchange.fetch_ohlcv(
                symbol=sym,
                timeframe=tf,
                limit=limit,
            )

            if not raw_candles:
                raise ValueError(f"Tidak ada data candlestick yang diterima untuk {sym} ({tf}).")

            df = pd.DataFrame(
                raw_candles,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )

            # Konversi tipe data ke float
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            # Tambahkan kolom waktu yang terbaca manusia
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")

            return df
        except Exception as e:
            logger.error(f"Gagal mengambil data OHLCV untuk {sym} ({tf}): {e}")
            raise

    def get_order_book(self, symbol: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Mengambil data buku pesanan (order book)."""
        sym = symbol or self.client.config.symbol
        try:
            return self.client.exchange.fetch_order_book(sym, limit=limit)
        except Exception as e:
            logger.error(f"Gagal mengambil order book untuk {sym}: {e}")
            raise
