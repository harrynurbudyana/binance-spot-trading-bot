"""
Skrip Pengecekan Saldo Akun Binance Spot Testnet (check_balance.py).
Menampilkan rincian saldo USDT dan aset kripto utama secara rapi.
Jalankan dengan:
    python check_balance.py
"""

from colorama import Fore, Style, init
from tabulate import tabulate

from src.config import load_config
from src.exchange import BinanceExchangeClient

init(autoreset=True)


def check_balance():
    print(Fore.CYAN + Style.BRIGHT + "\n" + "=" * 60)
    print(Fore.CYAN + Style.BRIGHT + "       INFORMASI SALDO AKUN BINANCE SPOT TESTNET")
    print(Fore.CYAN + Style.BRIGHT + "=" * 60 + "\n")

    config = load_config()
    client = BinanceExchangeClient(config)

    if not config.has_valid_api_keys:
        print(Fore.RED + "Error: Kunci API belum diatur pada file .env!")
        return

    try:
        balance = client.exchange.fetch_balance()
    except Exception as e:
        print(Fore.RED + f"Gagal mengambil saldo dari bursa: {e}")
        return

    # 1. Saldo USDT (Modal Trading Bot)
    free_usdt = float(balance.get("free", {}).get("USDT", 0.0) or 0.0)
    used_usdt = float(balance.get("used", {}).get("USDT", 0.0) or 0.0)
    total_usdt = float(balance.get("total", {}).get("USDT", 0.0) or 0.0)

    print(Fore.YELLOW + Style.BRIGHT + ">>> SALDO MODAL TRADING (USDT) <<<")
    print(f" • Saldo Bebas (Bisa Dipakai Beli) : {Fore.GREEN + Style.BRIGHT}{free_usdt:,.2f} USDT")
    print(f" • Saldo Terkunci (Dalam Order)     : {Fore.WHITE}{used_usdt:,.2f} USDT")
    print(f" • Total Saldo USDT                 : {Fore.CYAN + Style.BRIGHT}{total_usdt:,.2f} USDT")

    # 2. Saldo Aset Kripto & Stablecoin Utama
    major_tokens = ["BTC", "ETH", "BNB", "SOL", "USDC", "FDUSD", "DOGE", "ADA", "XRP"]
    rows = []

    for asset in major_tokens:
        total = float(balance.get("total", {}).get(asset, 0.0) or 0.0)
        free = float(balance.get("free", {}).get(asset, 0.0) or 0.0)
        used = float(balance.get("used", {}).get(asset, 0.0) or 0.0)
        if total > 0:
            rows.append([asset, f"{free:.4f}", f"{used:.4f}", f"{total:.4f}"])

    if rows:
        print("\n" + Fore.YELLOW + Style.BRIGHT + ">>> SALDO ASET KRIPTO UTAMA <<<")
        print(
            tabulate(
                rows,
                headers=["Aset", "Bebas (Free)", "Dalam Order (Used)", "Total Koin"],
                tablefmt="fancy_grid",
            )
        )

    print("\n" + Fore.CYAN + "=" * 60 + "\n")


if __name__ == "__main__":
    check_balance()
