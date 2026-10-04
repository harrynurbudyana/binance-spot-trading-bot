"""
Modul Rekayasa Fitur Teknikal (Feature Engineering) untuk Model AI.
Menghitung indikator teknikal dari data lilin OHLCV:
- RSI (14 & 7)
- MACD & Histogram
- Bollinger Bands (%B & Bandwidth)
- Moving Average Ratios (EMA 9, 21, 50)
- ATR (Average True Range / Volatilitas)
- Volume Momentum
"""

from typing import List, Tuple
import pandas as pd
import numpy as np


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Menghitung RSI menggunakan metode Wilder's Smoothing."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, 1e-10)
    return 100.0 - (100.0 / (1.0 + rs))


def extract_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Mengekstrak fitur-fitur teknikal prediktif dari DataFrame lilin OHLCV.
    Mengembalikan DataFrame dengan kolom fitur baru beserta daftar nama fitur.
    """
    df = df.copy()

    # Pastikan tipe numerik
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # 1. Price Returns & Momentum
    df["ret_1"] = close.pct_change(1)
    df["ret_3"] = close.pct_change(3)
    df["ret_5"] = close.pct_change(5)

    # 2. RSI (14 & 7)
    df["rsi_14"] = compute_rsi(close, period=14)
    df["rsi_7"] = compute_rsi(close, period=7)
    df["rsi_14_diff"] = df["rsi_14"].diff(1)

    # 3. EMA & Spreads
    ema_9 = close.ewm(span=9, adjust=False).mean()
    ema_21 = close.ewm(span=21, adjust=False).mean()
    ema_50 = close.ewm(span=50, adjust=False).mean()

    df["ema_9_21_ratio"] = (ema_9 / ema_21) - 1.0
    df["ema_21_50_ratio"] = (ema_21 / ema_50) - 1.0
    df["close_ema_21"] = (close / ema_21) - 1.0

    # 4. MACD
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - macd_signal

    df["macd_hist_norm"] = macd_hist / close
    df["macd_line_norm"] = macd_line / close

    # 5. Bollinger Bands
    rolling_mean_20 = close.rolling(20).mean()
    rolling_std_20 = close.rolling(20).std()
    bb_upper = rolling_mean_20 + (2.0 * rolling_std_20)
    bb_lower = rolling_mean_20 - (2.0 * rolling_std_20)

    # %B: Posisi harga relatif terhadap pita BB (0.0 = Lower, 1.0 = Upper)
    df["bb_percent_b"] = (close - bb_lower) / (bb_upper - bb_lower + 1e-10)
    df["bb_bandwidth"] = (bb_upper - bb_lower) / rolling_mean_20

    # 6. Volatilitas (ATR)
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_14 = tr.rolling(14).mean()
    df["atr_norm"] = atr_14 / close

    # 7. Bentuk Lilin (Candlestick Geometry)
    df["candle_body"] = (close - df["open"]) / close
    df["candle_range"] = (high - low) / close

    # 8. Volume Momentum
    vol_sma_20 = volume.rolling(20).mean()
    df["volume_ratio"] = volume / (vol_sma_20 + 1e-10)
    df["volume_change"] = volume.pct_change(1)

    feature_cols = [
        "ret_1", "ret_3", "ret_5",
        "rsi_14", "rsi_7", "rsi_14_diff",
        "ema_9_21_ratio", "ema_21_50_ratio", "close_ema_21",
        "macd_hist_norm", "macd_line_norm",
        "bb_percent_b", "bb_bandwidth",
        "atr_norm", "candle_body", "candle_range",
        "volume_ratio", "volume_change",
    ]

    return df, feature_cols
