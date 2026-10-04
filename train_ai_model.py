"""
Skrip Pelatihan Model AI Machine Learning untuk Trading Kripto (train_ai_model.py).
Membaca data lilin historis, mengekstrak fitur teknikal, melatih model prediktif,
mengevaluasi metrik akurasi & win-rate, lalu menyimpan model ke models/ai_trading_model.joblib.
"""

import os
import sys
from datetime import datetime
import argparse
import joblib
import pandas as pd
import numpy as np
from colorama import Fore, Style, init
from tabulate import tabulate

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import classification_report, accuracy_score, roc_auc_score, confusion_matrix

from src.features import extract_features

init(autoreset=True)


def build_targets(df: pd.DataFrame, horizon: int = 3, profit_target: float = 0.01, max_drawdown: float = -0.015) -> pd.Series:
    """
    Membuat label target (1 / 0) berdasarkan pergerakan harga di masa depan:
    - 1: Jika dalam horizon lilin ke depan, harga naik >= profit_target (1.0%)
         DAN harga terendah tidak menyentuh batas drawdown/stop loss (max_drawdown -1.5%).
    - 0: Jika kondisi di atas tidak terpenuhi.
    """
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    n = len(df)

    targets = np.zeros(n, dtype=int)

    for i in range(n - horizon):
        entry_price = close[i]
        future_highs = high[i + 1 : i + horizon + 1]
        future_lows = low[i + 1 : i + horizon + 1]

        max_return = (np.max(future_highs) - entry_price) / entry_price
        min_return = (np.min(future_lows) - entry_price) / entry_price

        if max_return >= profit_target and min_return > max_drawdown:
            targets[i] = 1
        else:
            targets[i] = 0

    # lilin terakhir yang tidak memiliki horizon penuh diberi nilai 0
    targets[n - horizon :] = 0
    return pd.Series(targets, index=df.index)


def train_model(
    data_path: str = "data/historical_candles_15m.csv",
    output_model_path: str = "models/ai_trading_model.joblib",
    model_type: str = "gradient_boosting",
):
    print(Fore.CYAN + Style.BRIGHT + "\n" + "=" * 65)
    print(Fore.CYAN + Style.BRIGHT + "    PELATIHAN MODEL AI MACHINE LEARNING TRADING")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65)
    print(f" Dataset Path     : {data_path}")
    print(f" Algoritma Model  : {model_type.upper()}")
    print(f" Output Model     : {output_model_path}")
    print("=" * 65 + "\n")

    if not os.path.exists(data_path):
        print(Fore.RED + f"Error: Dataset {data_path} tidak ditemukan!")
        print("Jalankan terlebih dahulu: python download_historical_data.py")
        sys.exit(1)

    print(Fore.YELLOW + "[1/5] Membaca dataset lilin historis...")
    df_raw = pd.read_csv(data_path)
    print(Fore.GREEN + f"  -> Berhasil memuat {len(df_raw):,} lilin.")

    print(Fore.YELLOW + "[2/5] Mengekstrak fitur-fitur teknikal prediktif...")
    df_features, feature_cols = extract_features(df_raw)

    print(Fore.YELLOW + "[3/5] Membangun label target trading (Horizon: 3 lilin, Profit: +1.0%, SL: -1.5%)...")
    df_features["target"] = build_targets(df_features, horizon=3, profit_target=0.01, max_drawdown=-0.015)

    # Buang baris dengan NaN akibat jendela rolling indikator awal (50 lilin pertama)
    df_clean = df_features.dropna().copy()
    # Hapus horizon terakhir
    df_clean = df_clean.iloc[:-3].copy()

    X = df_clean[feature_cols]
    y = df_clean["target"]

    target_1_count = (y == 1).sum()
    target_0_count = (y == 0).sum()
    print(
        Fore.GREEN
        + f"  -> Data latih bersih: {len(X):,} baris. "
        + f"Peluang Naik (1): {target_1_count:,} ({target_1_count/len(X)*100:.1f}%), "
        + f"Netral/Turun (0): {target_0_count:,} ({target_0_count/len(X)*100:.1f}%)"
    )

    # Time-Series Split (80% Train, 20% Test) - Tanpa Shuffle untuk menjaga urutan waktu
    split_idx = int(len(X) * 0.80)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print(Fore.YELLOW + f"[4/5] Melatih model {model_type.upper()} pada {len(X_train):,} sampel data...")

    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    if model_type == "random_forest":
        model = RandomForestClassifier(
            n_estimators=150,
            max_depth=5,
            min_samples_split=15,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
    else:
        model = GradientBoostingClassifier(
            n_estimators=120,
            learning_rate=0.05,
            max_depth=3,
            min_samples_split=15,
            random_state=42,
        )

    model.fit(X_train_scaled, y_train)

    print(Fore.YELLOW + "[5/5] Mengevaluasi performa model pada data uji masa depan (Out-of-Sample Test)...")
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)

    print(Fore.GREEN + Style.BRIGHT + "\n=== HASIL EVALUASI MODEL AI (TEST SET) ===")
    print(f" Akurasi Global   : {acc * 100:.2f}%")
    print(f" ROC-AUC Score    : {roc_auc:.3f}")

    # Top Feature Importance
    importances = model.feature_importances_
    feat_imp = sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True)

    print("\n" + Fore.CYAN + Style.BRIGHT + "Top 7 Indikator Paling Berpengaruh (Feature Importance):")
    imp_table = [[idx + 1, feat, f"{val*100:.2f}%"] for idx, (feat, val) in enumerate(feat_imp[:7])]
    print(tabulate(imp_table, headers=["No", "Nama Fitur / Indikator", "Bobot Pengaruh"], tablefmt="fancy_grid"))

    # Simpan model & metadata
    os.makedirs(os.path.dirname(output_model_path), exist_ok=True)
    artifact = {
        "model": model,
        "scaler": scaler,
        "feature_cols": feature_cols,
        "model_type": model_type,
        "accuracy": acc,
        "roc_auc": roc_auc,
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_trained_samples": len(X_train),
    }

    joblib.dump(artifact, output_model_path)
    print(Fore.GREEN + Style.BRIGHT + f"\n[SUKSES] Model AI berhasil disimpan ke: {output_model_path}\n")
    return artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train AI Trading Model")
    parser.add_argument("--data", type=str, default="data/historical_candles_15m.csv", help="Dataset path")
    parser.add_argument("--output", type=str, default="models/ai_trading_model.joblib", help="Output model path")
    parser.add_argument(
        "--model",
        type=str,
        default="gradient_boosting",
        choices=["gradient_boosting", "random_forest"],
        help="Algorithm type",
    )

    args = parser.parse_args()
    train_model(data_path=args.data, output_model_path=args.output, model_type=args.model)
