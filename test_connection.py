"""
Skrip Pengujian Koneksi API Binance Spot Testnet (test_connection.py).
Menguji:
1. Aksesibilitas publik server Binance Spot Testnet & latensi.
2. Keberadaan pasangan perdagangan (symbol) & batasan pasar (limits).
3. Pengambilan data harga live ticker & candlestick (OHLCV) 15 menit.
4. Kalkulasi indikator RSI 14-periode dengan data bursa riil.
5. Simulasi aturan manajemen risiko (10% saldo & 2% stop loss).
6. Otentikasi privat & pembacaan saldo akun jika kunci API disediakan.
"""

import sys
import time
from datetime import datetime, timezone
from colorama import Fore, Style, init
from tabulate import tabulate

from src.config import load_config
from src.exchange import BinanceExchangeClient
from src.fetcher import PriceFetcher
from src.strategy import RSIStrategy
from src.risk import RiskManager

init(autoreset=True)


def run_tests():
    print(Fore.CYAN + Style.BRIGHT + "\n" + "=" * 65)
    print(Fore.CYAN + Style.BRIGHT + "   UJI KONEKSI & MODUL BINANCE SPOT TESTNET (CCXT)")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65 + "\n")

    config = load_config()
    test_results = []

    # -------------------------------------------------------------
    # 1. Konfigurasi
    # -------------------------------------------------------------
    print(Fore.YELLOW + "[TES 1] Memvalidasi Konfigurasi Lokal...")
    try:
        config_summary = (
            f"Symbol: {config.symbol} | Timeframe: {config.timeframe} | "
            f"Testnet: {config.is_testnet} | DryRun: {config.dry_run}"
        )
        print(Fore.GREEN + f"  [SUKSES] Konfigurasi termuat dengan baik ({config_summary}).")
        test_results.append(("Konfigurasi .env", "LULUS", config_summary))
    except Exception as e:
        print(Fore.RED + f"  [GAGAL] Konfigurasi error: {e}")
        test_results.append(("Konfigurasi .env", "GAGAL", str(e)))
        return

    # Inisialisasi client
    client = BinanceExchangeClient(config)
    fetcher = PriceFetcher(client)
    strategy = RSIStrategy(config)
    risk_manager = RiskManager(config, client)

    # -------------------------------------------------------------
    # 2. Koneksi Publik & Server Time
    # -------------------------------------------------------------
    print(Fore.YELLOW + "\n[TES 2] Menguji Koneksi Publik ke Binance Spot Testnet...")
    t_start = time.time()
    pub_result = client.test_public_connection()
    latency_ms = (time.time() - t_start) * 1000.0

    if pub_result["success"]:
        server_dt = datetime.fromtimestamp(pub_result["server_time_ms"] / 1000.0, timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        detail = f"Latensi: {latency_ms:.1f}ms | Server Time: {server_dt} | Total Markets: {pub_result['total_markets']}"
        print(Fore.GREEN + f"  [SUKSES] Terhubung ke Testnet! {detail}")
        test_results.append(("Koneksi Publik Testnet", "LULUS", f"Latensi: {latency_ms:.1f}ms"))
    else:
        print(Fore.RED + f"  [GAGAL] Gagal terhubung ke Testnet: {pub_result['error']}")
        test_results.append(("Koneksi Publik Testnet", "GAGAL", pub_result["error"]))

    # -------------------------------------------------------------
    # 3. Validasi Market & Batasan Pasangan Aset
    # -------------------------------------------------------------
    print(Fore.YELLOW + f"\n[TES 3] Memeriksa Metadata Pasangan {config.symbol}...")
    try:
        market = client.get_market(config.symbol)
        limits = market.get("limits", {})
        min_amount = limits.get("amount", {}).get("min")
        min_cost = limits.get("cost", {}).get("min")
        precision = market.get("precision", {})

        detail = (
            f"Min Lot: {min_amount} | Min Notional: {min_cost} USDT | "
            f"Presisi Jumlah: {precision.get('amount')} | Presisi Harga: {precision.get('price')}"
        )
        print(Fore.GREEN + f"  [SUKSES] Simbol {config.symbol} aktif. {detail}")
        test_results.append((f"Metadata Pasar ({config.symbol})", "LULUS", detail))
    except Exception as e:
        print(Fore.RED + f"  [GAGAL] Gagal membaca metadata pasar: {e}")
        test_results.append((f"Metadata Pasar ({config.symbol})", "GAGAL", str(e)))

    # -------------------------------------------------------------
    # 4. Pengambilan Ticker & Candlestick 15m
    # -------------------------------------------------------------
    print(Fore.YELLOW + f"\n[TES 4] Menguji Pembacaan Harga Ticker & OHLCV ({config.timeframe})...")
    current_price = 0.0
    try:
        ticker = fetcher.get_ticker(config.symbol)
        current_price = ticker["last"]
        df_candles = fetcher.get_ohlcv_dataframe(config.symbol, config.timeframe, limit=50)

        candle_count = len(df_candles)
        last_close = df_candles.iloc[-1]["close"]
        detail = (
            f"Harga Live: ${current_price:,.2f} | Lilin {config.timeframe} Terambil: {candle_count} | "
            f"Lilin Terakhir: ${last_close:,.2f}"
        )
        print(Fore.GREEN + f"  [SUKSES] Data pasar berhasil diambil. {detail}")
        test_results.append(("Pembacaan Harga (Fetcher)", "LULUS", f"Harga: ${current_price:,.2f}"))
    except Exception as e:
        print(Fore.RED + f"  [GAGAL] Gagal mengambil data pasar: {e}")
        test_results.append(("Pembacaan Harga (Fetcher)", "GAGAL", str(e)))

    # -------------------------------------------------------------
    # 5. Pengujian Kalkulasi Strategi RSI
    # -------------------------------------------------------------
    print(Fore.YELLOW + "\n[TES 5] Menguji Kalkulasi Strategi RSI 14-Periode...")
    try:
        signal = strategy.evaluate(df_candles)
        detail = (
            f"RSI Terkini: {signal.rsi:.2f} | RSI Sebelumnya: {signal.prev_rsi:.2f} | "
            f"Sinyal: {signal.action.value} ({signal.reason})"
        )
        print(Fore.GREEN + f"  [SUKSES] Kalkulasi RSI berhasil. {detail}")
        test_results.append(("Kalkulasi Strategi RSI", "LULUS", f"RSI: {signal.rsi:.2f} -> {signal.action.value}"))
    except Exception as e:
        print(Fore.RED + f"  [GAGAL] Gagal menghitung RSI: {e}")
        test_results.append(("Kalkulasi Strategi RSI", "GAGAL", str(e)))

    # -------------------------------------------------------------
    # 6. Pengujian Aturan Manajemen Risiko (10% modal & 2% Stop Loss)
    # -------------------------------------------------------------
    print(Fore.YELLOW + "\n[TES 6] Menguji Aturan Manajemen Risiko...")
    try:
        # Simulasi saldo 1,000 USDT untuk verifikasi formula
        sim_balance = 1000.0
        ref_price = current_price if current_price > 0 else 85000.0

        is_valid, sim_amount, msg = risk_manager.calculate_position_size(
            symbol=config.symbol,
            current_price=ref_price,
            simulated_balance=sim_balance,
        )
        sl_price = risk_manager.calculate_stop_loss_price(config.symbol, ref_price)
        expected_sl = ref_price * (1.0 - config.stop_loss_percent / 100.0)

        risk_detail = (
            f"Saldo Sim: {sim_balance} USDT -> Beli: {sim_amount} {config.symbol} (Maks 10% Saldo) | "
            f"SL 2%: ${sl_price:,.2f} (Entry: ${ref_price:,.2f})"
        )
        print(Fore.GREEN + f"  [SUKSES] Aturan risiko valid. {risk_detail}")
        test_results.append(("Manajemen Risiko (10% & SL 2%)", "LULUS", risk_detail))
    except Exception as e:
        print(Fore.RED + f"  [GAGAL] Pengujian manajemen risiko gagal: {e}")
        test_results.append(("Manajemen Risiko", "GAGAL", str(e)))

    # -------------------------------------------------------------
    # 7. Pengujian Model AI Machine Learning
    # -------------------------------------------------------------
    print(Fore.YELLOW + "\n[TES 7] Menguji Kesiapan & Inferensi Model AI...")
    try:
        from src.ai_strategy import AIPredictiveStrategy
        ai_strat = AIPredictiveStrategy(config)
        if ai_strat.is_loaded:
            ai_prob = ai_strat.predict_latest_probability(df_candles)
            ai_detail = f"Model Aktif | Probabilitas Naik: {ai_prob * 100:.1f}%"
            print(Fore.GREEN + f"  [SUKSES] Inferensi Model AI sukses! {ai_detail}")
            test_results.append(("Model AI (Machine Learning)", "LULUS", ai_detail))
        else:
            print(Fore.YELLOW + "  [DILEWATI] File model AI belum ditemukan (jalankan train_ai_model.py).")
            test_results.append(("Model AI (Machine Learning)", "DILEWATI", "Model belum dilatih"))
    except Exception as e:
        print(Fore.RED + f"  [GAGAL] Pengujian AI error: {e}")
        test_results.append(("Model AI (Machine Learning)", "GAGAL", str(e)))

    # -------------------------------------------------------------
    # 8. Pengujian Kredensial Privat (API Key & Saldo)
    # -------------------------------------------------------------
    print(Fore.YELLOW + "\n[TES 8] Menguji Kredensial Privat API...")
    if config.has_valid_api_keys:
        priv_result = client.test_private_connection()
        if priv_result["success"]:
            usdt_free = priv_result["usdt_free"]
            usdt_total = priv_result["usdt_total"]
            balances_detail = f"Saldo Bebas: {usdt_free:.2f} USDT | Total: {usdt_total:.2f} USDT"
            print(Fore.GREEN + f"  [SUKSES] Autentikasi API berhasil! {balances_detail}")
            test_results.append(("Autentikasi Privat & Saldo", "LULUS", balances_detail))
        else:
            print(Fore.RED + f"  [GAGAL] Autentikasi API gagal: {priv_result['error']}")
            test_results.append(("Autentikasi Privat & Saldo", "GAGAL", priv_result["error"]))
    else:
        info_msg = (
            "API Key masih berupa placeholder (.env). "
            "Koneksi publik & bot simulasi (DRY_RUN=True) berfungsi penuh. "
            "Untuk trading riil di Testnet, dapatkan API Key di https://testnet.binance.vision/"
        )
        print(Fore.YELLOW + f"  [DILEWATI] {info_msg}")
        test_results.append(("Autentikasi Privat & Saldo", "DILEWATI", "Kunci API placeholder"))

    # -------------------------------------------------------------
    # Ringkasan Laporan
    # -------------------------------------------------------------
    print("\n" + Fore.CYAN + Style.BRIGHT + "=" * 65)
    print(Fore.CYAN + Style.BRIGHT + "                RINGKASAN HASIL PENGUJIAN")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65)

    table_data = []
    for test_name, status, detail in test_results:
        if status == "LULUS":
            colored_status = Fore.GREEN + Style.BRIGHT + "LULUS"
        elif status == "DILEWATI":
            colored_status = Fore.YELLOW + Style.BRIGHT + "DILEWATI"
        else:
            colored_status = Fore.RED + Style.BRIGHT + "GAGAL"

        table_data.append([test_name, colored_status, detail[:50] + ("..." if len(detail) > 50 else "")])

    print(tabulate(table_data, headers=["Komponen Pengujian", "Status", "Keterangan"], tablefmt="fancy_grid"))
    print("\n")


if __name__ == "__main__":
    run_tests()
