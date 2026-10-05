"""
Modul Strategi Trading RSI Sederhana.
Menghitung indikator Relative Strength Index (RSI) dan menghasilkan sinyal trading:
- BELI jika RSI < 30 (Kondisi Oversold pada timeframe 15m)
- JUAL jika RSI > 70 (Kondisi Overbought untuk take-profit)
- TAHAN (HOLD) jika di antara rentang tersebut
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import pandas as pd
from src.config import BotConfig

logger = logging.getLogger("RSIStrategy")


class SignalAction(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class StrategySignal:
    """Representasi sinyal yang dihasilkan oleh strategi."""
    action: SignalAction
    rsi: float
    prev_rsi: float
    price: float
    reason: str
    timeframe: str
    ma200: Optional[float] = None


class RSIStrategy:
    """Implementasi strategi RSI sederhana (Wilder's Smoothing)."""

    def __init__(self, config: BotConfig):
        self.config = config
        self.period = config.rsi_period
        self.oversold = config.rsi_oversold
        self.overbought = config.rsi_overbought

    def calculate_rsi(self, df: pd.DataFrame) -> pd.Series:
        """
        Menghitung RSI menggunakan metode standar Wilder's Smoothing
        (seperti yang digunakan oleh TradingView dan Binance).
        """
        if len(df) < self.period + 1:
            raise ValueError(
                f"Data tidak cukup untuk menghitung RSI {self.period} periode. "
                f"Dibutuhkan minimal {self.period + 1} lilin (candle), tersedia {len(df)}."
            )

        close = df["close"]
        delta = close.diff()

        # Pisahkan kenaikan (gain) dan penurunan (loss)
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)

        # Gunakan exponential moving average dengan alpha = 1 / period (Wilder's smoothing)
        avg_gain = gain.ewm(alpha=1.0 / self.period, min_periods=self.period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / self.period, min_periods=self.period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0.0, 1e-10)
        rsi = 100.0 - (100.0 / (1.0 + rs))

        return rsi

    def evaluate(self, df: pd.DataFrame) -> StrategySignal:
        """
        Menganalisis DataFrame candle terbaru dan menghasilkan sinyal trading.
        """
        df_copy = df.copy()
        df_copy["rsi"] = self.calculate_rsi(df_copy)
        df_copy["ma200"] = df_copy["close"].rolling(window=200).mean()

        current_candle = df_copy.iloc[-1]
        prev_candle = df_copy.iloc[-2]

        current_rsi = float(current_candle["rsi"])
        prev_rsi = float(prev_candle["rsi"])
        current_price = float(current_candle["close"])
        current_ma200 = float(current_candle["ma200"]) if pd.notna(current_candle.get("ma200")) else 0.0

        # Evaluasi aturan strategi dinamis (Momentum) dengan Trend Filter MA200
        if current_rsi <= (prev_rsi - 3.0):
            if current_ma200 > 0 and current_price < current_ma200:
                action = SignalAction.HOLD
                reason = (
                    f"RSI Beli terpenuhi, tapi Harga ({current_price:.4f}) di Bawah MA200 ({current_ma200:.4f}). "
                    f"Tren Sedang Turun -> DIBATALKAN (HOLD)."
                )
            else:
                action = SignalAction.BUY
                reason = (
                    f"RSI Turun >= 3 poin (Saat ini: {current_rsi:.2f}) & Harga > MA200 -> Sinyal BELI."
                )
        elif current_rsi > prev_rsi:
            action = SignalAction.SELL
            reason = (
                f"RSI Naik (Saat ini: {current_rsi:.2f}, Prev: {prev_rsi:.2f}) "
                f"pada timeframe {self.config.timeframe} -> Sinyal JUAL (Take Profit)."
            )
        else:
            action = SignalAction.HOLD
            reason = (
                f"RSI Stagnan/Turun kecil (Saat ini: {current_rsi:.2f}, Prev: {prev_rsi:.2f}) "
                f"-> TAHAN (HOLD)."
            )

        return StrategySignal(
            action=action,
            rsi=current_rsi,
            prev_rsi=prev_rsi,
            price=current_price,
            reason=reason,
            timeframe=self.config.timeframe,
            ma200=current_ma200,
        )
