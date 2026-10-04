"""
Skrip Pengunduh Data Historis Lilin (Candlestick) dari Bursa Binance.
Mengunduh ribuan data lilin 15m untuk melatih model AI Machine Learning.
Data disimpan ke file CSV di folder data/.
"""

import os
import sys
import time
from datetime import datetime, timezone
import argparse
import ccxt
import pandas as pd
from colorama import Fore, Style, init

init(autoreset=True)


def download_candles(
    symbol: str = "BTC/USDT",
    timeframe: str = "15m",
    total_candles: int = 5000,
    output_path: str = "data/historical_candles_15m.csv",
):
    print(Fore.CYAN + Style.BRIGHT + "\n" + "=" * 65)
    print(Fore.CYAN + Style.BRIGHT + "    PENGUNDUH DATA HISTORIS PASAR (BINANCE)")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65)
    print(f" Simbol           : {symbol}")
    print(f" Timeframe        : {timeframe}")
    print(f" Target Lilin     : {total_candles:,} candle")
    print(f" Output File      : {output_path}")
    print("=" * 65 + "\n")

    exchange = ccxt.binance({"enableRateLimit": True})

    # Hitung perkiraan titik awal mundur dari waktu sekarang
    # 15 menit = 15 * 60 * 1000 ms
    tf_minutes = 15
    if timeframe.endswith("m"):
        tf_minutes = int(timeframe[:-1])
    elif timeframe.endswith("h"):
        tf_minutes = int(timeframe[:-1]) * 60

    ms_per_candle = tf_minutes * 60 * 1000
    total_duration_ms = total_candles * ms_per_candle
    now_ms = exchange.milliseconds()
    start_since = now_ms - total_duration_ms

    all_candles = []
    current_since = start_since
    batch_size = 1000

    print(Fore.YELLOW + "Memulai proses pengunduhan batch dari Binance...")

    while len(all_candles) < total_candles:
        try:
            candles = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=current_since,
                limit=batch_size,
            )

            if not candles:
                print(Fore.YELLOW + "Tidak ada lilin baru yang tersedia dari endpoint.")
                break

            all_candles.extend(candles)
            last_timestamp = candles[-1][0]
            current_since = last_timestamp + ms_per_candle

            last_dt = datetime.fromtimestamp(last_timestamp / 1000.0, timezone.utc).strftime(
                "%Y-%m-%d %H:%M"
            )
            print(
                Fore.GREEN
                + f"  -> Berhasil mengunduh {len(all_candles):,} / {total_candles:,} lilin "
                + f"(Sampai dengan: {last_dt} UTC)"
            )

            # Jika timestamp terakhir sudah mendekati waktu sekarang, hentikan
            if last_timestamp >= now_ms - (ms_per_candle * 2):
                break

            time.sleep(exchange.rateLimit / 1000.0)

        except Exception as e:
            print(Fore.RED + f"Gagal pada batch pengunduhan: {e}. Mengulang dalam 2 detik...")
            time.sleep(2)

    # Hilangkan duplikat timestamp jika ada
    df = pd.DataFrame(
        all_candles,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )
    df.drop_duplicates(subset=["timestamp"], inplace=True)
    df.sort_values(by="timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Tambahkan kolom waktu ISO terbaca
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    print(Fore.CYAN + Style.BRIGHT + "\n" + "=" * 65)
    print(Fore.GREEN + Style.BRIGHT + f"[SELESAI] Total {len(df):,} data lilin berhasil disimpan ke:")
    print(Fore.WHITE + f" -> {output_path}")
    print(f" Rentang Waktu: {df['datetime'].iloc[0]} s/d {df['datetime'].iloc[-1]}")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65 + "\n")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Historical Candlestick Data from Binance")
    parser.add_argument("--symbol", type=str, default="BTC/USDT", help="Trading pair symbol (default: BTC/USDT)")
    parser.add_argument("--timeframe", type=str, default="15m", help="Candle timeframe (default: 15m)")
    parser.add_argument("--candles", type=int, default=5000, help="Number of candles to download (default: 5000)")
    parser.add_argument("--output", type=str, default="data/historical_candles_15m.csv", help="Output CSV path")

    args = parser.parse_args()
    download_candles(
        symbol=args.symbol,
        timeframe=args.timeframe,
        total_candles=args.candles,
        output_path=args.output,
    )
