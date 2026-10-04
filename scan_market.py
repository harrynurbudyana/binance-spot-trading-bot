"""
Skrip Pemindai Pasar Kripto Live (scan_market.py).
Memindai daftar koin unggulan di Binance Spot Testnet, menghitung RSI dan harga terkini,
lalu mengurutkan dari yang paling oversold (diskon/peluang beli) hingga overbought.
Jalankan dengan:
    python scan_market.py
"""

from colorama import Fore, Style, init
from tabulate import tabulate

from src.config import load_config
from src.exchange import BinanceExchangeClient
from src.fetcher import PriceFetcher
from src.strategy import RSIStrategy

init(autoreset=True)


def scan_markets(timeframe: str = "3m"):
    print(Fore.CYAN + Style.BRIGHT + "\n" + "=" * 65)
    print(Fore.CYAN + Style.BRIGHT + f"   PEMINDAI PASAR REAL-TIME BINANCE SPOT TESTNET ({timeframe})")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65 + "\n")

    config = load_config()
    client = BinanceExchangeClient(config)
    fetcher = PriceFetcher(client)
    strategy = RSIStrategy(config)

    # Watchlist koin populer dengan volume tinggi
    watchlist = config.symbols_to_scan
    default_coins = ["SOL/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "BTC/USDT", "ETH/USDT", "BNB/USDT"]
    for c in default_coins:
        if c not in watchlist:
            watchlist.append(c)

    results = []

    print(Fore.YELLOW + f"Memindai {len(watchlist)} pasangan kripto...")

    for symbol in watchlist:
        try:
            df = fetcher.get_ohlcv_dataframe(symbol=symbol, timeframe=timeframe, limit=50)
            sig = strategy.evaluate(df)
            price = sig.price
            rsi = sig.rsi

            if rsi < config.rsi_oversold:
                status_str = Fore.GREEN + Style.BRIGHT + f"🔥 DISKON (RSI < {config.rsi_oversold})"
            elif rsi > config.rsi_overbought:
                status_str = Fore.YELLOW + f"⚠️  OVERBOUGHT (> {config.rsi_overbought})"
            else:
                status_str = Fore.WHITE + "NETRAL"

            results.append([symbol, price, rsi, status_str])
        except Exception as e:
            results.append([symbol, 0.0, 50.0, f"Error: {e}"])

    # Urutkan dari RSI terendah (paling oversold / paling potensial)
    results.sort(key=lambda x: x[2])

    table_data = []
    for rank, (sym, price, rsi, status) in enumerate(results, 1):
        rsi_color = Fore.GREEN if rsi < config.rsi_oversold else (Fore.YELLOW if rsi > config.rsi_overbought else Fore.WHITE)
        table_data.append([rank, sym, f"${price:,.4f}", f"{rsi_color}{rsi:.2f}{Fore.RESET}", status])

    print("\n" + tabulate(table_data, headers=["No", "Simbol", "Harga Terkini", f"RSI {timeframe}", "Status Scalping"], tablefmt="fancy_grid"))
    print("\n" + Fore.CYAN + "=" * 65 + "\n")


if __name__ == "__main__":
    scan_markets()
