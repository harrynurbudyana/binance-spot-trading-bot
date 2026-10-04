"""
Modul Strategi Trading Berbasis AI Machine Learning (src/ai_strategy.py).
Memuat model AI terlatih (models/ai_trading_model.joblib), mengekstrak fitur real-time,
dan menghasilkan sinyal trading dengan probabilitas kecerdasan buatan.
Mendukung mode HYBRID (RSI + AI Filter) dan mode AI_ONLY.
"""

import os
import logging
from typing import Optional, Dict, Any
import joblib
import pandas as pd
import numpy as np

from src.config import BotConfig
from src.strategy import SignalAction, StrategySignal, RSIStrategy
from src.features import extract_features

logger = logging.getLogger("AIStrategy")


class AIPredictiveStrategy:
    """Strategi trading prediktif menggunakan model Machine Learning terlatih."""

    def __init__(self, config: BotConfig, model_path: str = "models/ai_trading_model.joblib"):
        self.config = config
        self.model_path = model_path
        self.rsi_fallback = RSIStrategy(config)

        self.model = None
        self.scaler = None
        self.feature_cols = []
        self.is_loaded = False

        self.confidence_threshold = getattr(config, "ai_confidence_threshold", 0.40)
        self.load_model()

    def load_model(self):
        """Memuat artefak model AI dari disk."""
        if not os.path.exists(self.model_path):
            logger.warning(
                f"Model AI di {self.model_path} belum ditemukan. "
                "Jalankan train_ai_model.py terlebih dahulu. Menggunakan strategi RSI standar."
            )
            self.is_loaded = False
            return

        try:
            artifact = joblib.load(self.model_path)
            self.model = artifact["model"]
            self.scaler = artifact["scaler"]
            self.feature_cols = artifact["feature_cols"]
            self.is_loaded = True
            logger.info(
                f"Model AI ({artifact.get('model_type')}) berhasil dimuat. "
                f"Akurasi Test: {artifact.get('accuracy', 0)*100:.2f}%, ROC-AUC: {artifact.get('roc_auc', 0):.3f}"
            )
        except Exception as e:
            logger.error(f"Gagal memuat model AI: {e}")
            self.is_loaded = False

    def predict_latest_probability(self, df: pd.DataFrame) -> float:
        """Menghitung probabilitas kenaikan harga pada lilin terbaru."""
        if not self.is_loaded:
            return 0.50

        # Ekstrak fitur teknikal dari data live
        df_feat, _ = extract_features(df)
        latest_row = df_feat.iloc[-1:][self.feature_cols]

        if latest_row.isnull().values.any():
            latest_row = latest_row.fillna(0.0)

        # Scale menggunakan scaler yang disimpan saat training
        X_scaled = self.scaler.transform(latest_row)

        # Prediksi probabilitas kelas 1 (Peluang Naik)
        proba = self.model.predict_proba(X_scaled)[0][1]
        return float(proba)

    def evaluate(self, df: pd.DataFrame) -> StrategySignal:
        """
        Mengevaluasi lilin pasar menggunakan model AI dan indikator teknikal.
        Mode Hybrid: Memvalidasi sinyal RSI dengan konfirmasi probabilitas model AI.
        """
        # Hitung sinyal dasar RSI
        rsi_signal = self.rsi_fallback.evaluate(df)
        current_price = rsi_signal.price
        current_rsi = rsi_signal.rsi
        prev_rsi = rsi_signal.prev_rsi

        if not self.is_loaded:
            # Fallback ke RSI jika model belum dilatih
            return rsi_signal

        ai_prob = self.predict_latest_probability(df)
        strategy_mode = getattr(self.config, "strategy_type", "HYBRID").upper()

        if strategy_mode == "HYBRID":
            # Mode Hybrid: Sinyal beli RSI < 30 divalidasi oleh AI
            if current_rsi < self.config.rsi_oversold:
                if ai_prob >= self.confidence_threshold:
                    action = SignalAction.BUY
                    reason = (
                        f"[AI HYBRID BUY] RSI ({current_rsi:.2f} < {self.config.rsi_oversold}) "
                        f"DIVALIDASI oleh AI (Keyakinan: {ai_prob*100:.1f}% >= {self.confidence_threshold*100:.1f}%)"
                    )
                else:
                    action = SignalAction.HOLD
                    reason = (
                        f"[AI FILTER DITOLAK] RSI Oversold ({current_rsi:.2f}), "
                        f"tetapi AI menolak karena probabilitas rendah ({ai_prob*100:.1f}% < {self.confidence_threshold*100:.1f}%)"
                    )
            elif current_rsi > self.config.rsi_overbought:
                action = SignalAction.SELL
                reason = f"[TAKE PROFIT] RSI Overbought ({current_rsi:.2f} > {self.config.rsi_overbought})"
            else:
                action = SignalAction.HOLD
                reason = (
                    f"[HOLD] RSI Netral ({current_rsi:.2f}), "
                    f"Probabilitas AI Naik: {ai_prob*100:.1f}%"
                )

        else:
            # Mode AI_ONLY
            if ai_prob >= self.confidence_threshold:
                action = SignalAction.BUY
                reason = f"[AI BUY] Probabilitas AI ({ai_prob*100:.1f}%) melampaui ambang batas ({self.confidence_threshold*100:.1f}%)"
            elif current_rsi > self.config.rsi_overbought:
                action = SignalAction.SELL
                reason = f"[AI SELL] RSI Overbought ({current_rsi:.2f})"
            else:
                action = SignalAction.HOLD
                reason = f"[AI HOLD] Probabilitas AI: {ai_prob*100:.1f}%"

        return StrategySignal(
            action=action,
            rsi=current_rsi,
            prev_rsi=prev_rsi,
            price=current_price,
            reason=reason,
            timeframe=self.config.timeframe,
        )
