import os
import ccxt
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
secret_key = os.getenv("BINANCE_SECRET_KEY")

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': secret_key,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot',
    },
})
exchange.set_sandbox_mode(True)

try:
    print("Fetching trades...")
    # Fetch orders might be easier than fetch_my_trades since we don't have to specify symbol
    # Actually ccxt fetch_my_trades without symbol might not be supported by binance
    # Let's fetch balances and compare against 10000 USDT.
    balance = exchange.fetch_balance()
    usdt_free = balance.get('USDT', {}).get('free', 0)
    usdt_used = balance.get('USDT', {}).get('used', 0)
    print(f"USDT Balance: {usdt_free + usdt_used}")
    
    # Let's check some symbols
    symbols = ['BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'ETH/USDT', 'BTC/USDT']
    for sym in symbols:
        trades = exchange.fetch_my_trades(sym, limit=20)
        if trades:
            print(f"--- Trades for {sym} ---")
            for t in trades[-5:]:
                print(f"{t['datetime']} | {t['side']} | {t['amount']} @ {t['price']} | cost: {t['cost']}")
except Exception as e:
    print(f"Error: {e}")
