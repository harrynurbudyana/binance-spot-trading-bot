"""
Titik Masuk Utama (Main Entry Point) Bot Trading Binance Spot Testnet.
Jalankan bot dengan:
    python main.py
"""

import sys
import logging
from src.config import load_config
from src.bot import CryptoTradingBot

# Konfigurasi logging standar
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

# Kurangi kebisingan log bawaan urllib3 dan ccxt jika tidak error
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("ccxt").setLevel(logging.WARNING)


def main():
    try:
        config = load_config()
        bot = CryptoTradingBot(config)
        bot.start()
    except Exception as e:
        print(f"\n[FATAL ERROR] Bot terhenti karena kesalahan sistem: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
