"""
Modul Utama Koordinator Bot Trading (CryptoTradingBot).
Mengintegrasikan modul client bursa, pembaca harga, strategi RSI, dan manajemen risiko ke dalam alur eksekusi otomatis.
"""

import time
import logging
from datetime import datetime
from typing import Optional
from colorama import Fore, Style, init

from src.config import BotConfig, load_config
from src.exchange import BinanceExchangeClient
from src.fetcher import PriceFetcher
from src.strategy import RSIStrategy, SignalAction
from src.ai_strategy import AIPredictiveStrategy
from src.risk import RiskManager, Position

init(autoreset=True)
logger = logging.getLogger("CryptoBot")


class CryptoTradingBot:
    """Mesin utama bot trading crypto otomatis."""

    def __init__(self, config: Optional[BotConfig] = None):
        self.config = config or load_config()
        self.client = BinanceExchangeClient(self.config)
        self.fetcher = PriceFetcher(self.client)

        # Inisialisasi strategi (AI Hybrid atau RSI murni)
        if self.config.strategy_type.upper() in ("HYBRID", "AI"):
            self.strategy = AIPredictiveStrategy(self.config)
        else:
            self.strategy = RSIStrategy(self.config)

        self.risk_manager = RiskManager(self.config, self.client)
        self.active_position: Optional[Position] = None
        self.is_running = False

        # Pelacakan Saldo & Akumulasi Keuntungan
        self.initial_balance = 0.0
        self.current_balance = 0.0
        self.total_profit_usdt = 0.0

    def initialize(self):
        """Memuat metadata pasar dan memvalidasi kesiapan bot."""
        print(Fore.CYAN + "\n[1/3] Menginisialisasi koneksi ke Binance Spot Testnet...")
        self.client.load_markets()
        
        symbols = self.config.symbols_to_scan
        print(Fore.CYAN + f" -> Memvalidasi {len(symbols)} pasangan aset scanner: {', '.join(symbols)}")
        for sym in symbols:
            try:
                self.client.get_market(sym)
                print(Fore.GREEN + f"    ✓ {sym} aktif di bursa.")
            except Exception as e:
                print(Fore.RED + f"    ✗ Peringatan: Pasangan {sym} bermasalah: {e}")

        print(Fore.CYAN + "[2/3] Memeriksa saldo akun...")
        if self.config.has_valid_api_keys:
            free_usdt = self.client.get_free_balance("USDT")
            self.initial_balance = free_usdt
            self.current_balance = free_usdt
            print(Fore.GREEN + f" -> Saldo USDT Bebas: {free_usdt:,.2f} USDT")
        else:
            self.initial_balance = 1000.0
            self.current_balance = 1000.0
            print(
                Fore.YELLOW
                + " -> Kunci API berupa placeholder. Mode simulasi aktif dengan saldo virtual 1,000.00 USDT."
            )

        print(Fore.CYAN + f"[3/3] Memeriksa lilin awal pasar ({self.config.timeframe})...")
        test_sym = symbols[0]
        df = self.fetcher.get_ohlcv_dataframe(symbol=test_sym, limit=210)
        signal = self.strategy.evaluate(df)
        print(
            Fore.GREEN
            + f" -> Data {self.config.timeframe} ({test_sym}) berhasil dimuat. RSI: {signal.rsi:.2f} (Harga: ${signal.price:,.4f})"
        )

    def execute_buy(self, symbol: Optional[str] = None, current_price: Optional[float] = None):
        """Mengeksekusi order beli berdasarkan aturan strategi dan manajemen risiko."""
        sym = symbol or self.config.symbol
        price = current_price if current_price is not None else self.fetcher.get_latest_price(sym)
        print(Fore.YELLOW + f"\n[!] Menganalisis ukuran posisi untuk sinyal BELI {sym}...")

        is_valid, amount, message = self.risk_manager.calculate_position_size(
            symbol=sym,
            current_price=price,
        )

        if not is_valid:
            print(Fore.RED + f" [DITOLAK MANAJEMEN RISIKO] {message}")
            return

        print(Fore.GREEN + f" [LOLOS MANAJEMEN RISIKO] {message}")

        # Hitung Stop Loss & Take Profit Scalping
        stop_loss_price = self.risk_manager.calculate_stop_loss_price(sym, price)
        take_profit_price = self.risk_manager.calculate_take_profit_price(sym, price)
        print(
            Fore.MAGENTA
            + f" -> Target TP Scalping : ${take_profit_price:,.4f} (+{self.config.take_profit_percent}%) | "
            + f"Stop Loss : ${stop_loss_price:,.4f} (-{self.config.stop_loss_percent}%)"
        )

        try:
            order = self.client.create_market_buy_order(sym, amount)
            order_id = str(order.get("id", "SIMULATED_ORDER"))

            self.active_position = Position(
                symbol=sym,
                entry_price=price,
                amount=amount,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                entry_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                order_id=order_id,
            )

            print(
                Fore.GREEN + Style.BRIGHT
                + f" >>> EKSEKUSI BELI BERHASIL: {amount} {sym} @ ${price:,.4f} <<<"
            )
        except Exception as e:
            print(Fore.RED + f"Gagal mengeksekusi order beli: {e}")

    def execute_sell(self, reason: str, current_price: float):
        """Mengeksekusi order jual untuk menutup posisi yang aktif."""
        if not self.active_position:
            return

        pos = self.active_position
        symbol = pos.symbol
        amount = pos.amount
        pnl_usdt, pnl_pct = pos.calculate_pnl(current_price)
        self.total_profit_usdt += pnl_usdt

        color = Fore.GREEN if pnl_pct >= 0 else Fore.RED
        print(
            color + Style.BRIGHT
            + f"\n[!] MENUTUP POSISI ({reason}): {amount} {symbol} @ ${current_price:,.2f}"
        )
        print(
            color
            + f"    Harga Beli (Entry): ${pos.entry_price:,.2f} | PnL: {pnl_usdt:+.2f} USDT ({pnl_pct:+.2f}%)"
        )

        try:
            self.client.create_market_sell_order(symbol, amount)
            self.active_position = None
            print(Fore.GREEN + " >>> EKSEKUSI JUAL BERHASIL. POSISI TELAH DITUTUP. <<<")

            # Update saldo terbaru
            time.sleep(1)
            balance_before = self.current_balance
            if self.config.has_valid_api_keys and not self.config.dry_run:
                new_balance = self.client.get_free_balance("USDT")
                diff = new_balance - balance_before
                self.current_balance = new_balance
            else:
                diff = pnl_usdt
                self.current_balance += pnl_usdt

            print("\n" + "=" * 60)
            if diff > 0 or pnl_usdt > 0:
                gain = diff if diff > 0 else pnl_usdt
                print(
                    Fore.GREEN + Style.BRIGHT
                    + f" 🎉 SALDO BERTAMBAH SEBANYAK: +{gain:,.2f} USDT! (+{pnl_pct:+.2f}%)"
                )
            else:
                loss = abs(diff) if diff < 0 else abs(pnl_usdt)
                print(
                    Fore.RED + Style.BRIGHT
                    + f" ⚠️  Saldo berkurang sebanyak: -{loss:,.2f} USDT ({pnl_pct:+.2f}%)"
                )

            print(Fore.CYAN + f"    • Total Saldo USDT Saat Ini : {self.current_balance:,.2f} USDT")
            print(Fore.CYAN + f"    • Akumulasi PnL Keseluruhan : {self.total_profit_usdt:+,.2f} USDT")
            print("=" * 60 + "\n")
        except Exception as e:
            print(Fore.RED + f"Gagal mengeksekusi order jual: {e}")

    def run_iteration(self, iteration: int):
        """Satu iterasi pemantauan pasar dan pengambilan keputusan."""
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Periksa apakah ada saldo bertambah di luar bot (deposit/faucet)
        if iteration % 4 == 0 and self.config.has_valid_api_keys and not self.config.dry_run:
            real_free = self.client.get_free_balance("USDT")
            if real_free > self.current_balance + 0.05:
                tambah = real_free - self.current_balance
                print(
                    Fore.GREEN + Style.BRIGHT
                    + f"\n✨ [UPDATE SALDO] Saldo bertambah sebanyak +{tambah:,.2f} USDT! "
                    + f"(Total Saldo: {real_free:,.2f} USDT)\n"
                )
            self.current_balance = real_free

        # KASUS 1: ADA POSISI AKTIF (Fokus Kelola Posisi Koin Ini Sampai Selesai)
        if self.active_position is not None:
            pos = self.active_position
            symbol = pos.symbol
            current_price = self.fetcher.get_latest_price(symbol)
            pnl_usdt, pnl_pct = pos.calculate_pnl(current_price)
            pnl_color = Fore.GREEN if pnl_pct >= 0 else Fore.RED

            df = self.fetcher.get_ohlcv_dataframe(symbol=symbol, limit=210)
            signal = self.strategy.evaluate(df)
            rsi = signal.rsi

            tp_str = f", TP=${pos.take_profit_price:,.4f}" if pos.take_profit_price > 0 else ""
            print(
                f"[{timestamp_str}] #{iteration} | {symbol} (${current_price:,.4f}) | "
                f"Saldo: {self.current_balance:,.2f} USDT | RSI {self.config.timeframe}: {rsi:.2f} | "
                f"POSISI: Entry=${pos.entry_price:,.4f}{tp_str}, SL=${pos.stop_loss_price:,.4f} | "
                + pnl_color
                + f"PnL: {pnl_usdt:+.2f} USDT ({pnl_pct:+.2f}%)"
            )

            # 1. Cek Stop Loss statis
            if self.risk_manager.is_stop_loss_triggered(pos, current_price):
                print(
                    Fore.RED + Style.BRIGHT
                    + f"\n[ALERT STOP LOSS] Harga ${current_price:,.4f} <= SL ${pos.stop_loss_price:,.4f}!"
                )
                self.execute_sell(reason=f"STOP LOSS TRIGGERED (-{self.config.stop_loss_percent}%)", current_price=current_price)
                return

            # 2. Cek Target Take Profit Scalping
            if self.risk_manager.is_take_profit_triggered(pos, current_price):
                print(
                    Fore.GREEN + Style.BRIGHT
                    + f"\n[ALERT TAKE PROFIT] Target Scalping Tercapai! (${current_price:,.4f} >= TP ${pos.take_profit_price:,.4f})"
                )
                self.execute_sell(reason=f"TAKE PROFIT TARGET (+{self.config.take_profit_percent}%)", current_price=current_price)
                return

            # 3. Cek Sinyal Jual Strategi (Take Profit saat RSI Naik)
            if signal.action == SignalAction.SELL:
                print(
                    Fore.GREEN + Style.BRIGHT
                    + f"\n[ALERT RSI MOMENTUM] Sinyal Jual Strategi Aktif (RSI {rsi:.2f})!"
                )
                self.execute_sell(reason="RSI MOMENTUM NAIK (TAKE PROFIT)", current_price=current_price)
                return

        # KASUS 2: TIDAK ADA POSISI AKTIF -> SCAN SEMUA KOIN DI WATCHLIST
        else:
            symbols_to_scan = self.config.symbols_to_scan
            candidates = []
            scan_parts = []

            for sym in symbols_to_scan:
                try:
                    df = self.fetcher.get_ohlcv_dataframe(symbol=sym, limit=210)
                    sig = self.strategy.evaluate(df)
                    coin = sym.split("/")[0]

                    color_code = (
                        Fore.GREEN
                        if sig.rsi < self.config.rsi_oversold
                        else (Fore.YELLOW if sig.rsi > self.config.rsi_overbought else Fore.WHITE)
                    )
                    scan_parts.append(f"{coin}:{color_code}{sig.rsi:.1f}{Fore.RESET}")

                    if sig.action == SignalAction.BUY:
                        candidates.append((sym, sig, sig.price, sig.rsi))
                except Exception as e:
                    logger.debug(f"Gagal memindai {sym}: {e}")

            scan_str = " | ".join(scan_parts)
            if candidates:
                # Urutkan koin berdasarkan RSI paling rendah (paling oversold / diskon terbesar)
                candidates.sort(key=lambda x: x[3])
                best_sym, best_sig, best_price, best_rsi = candidates[0]

                print(
                    f"[{timestamp_str}] #{iteration} | Saldo: {self.current_balance:,.2f} USDT | [SCAN {self.config.timeframe}] {scan_str}"
                )
                print(
                    Fore.GREEN + Style.BRIGHT
                    + f"\n🎯 [PELUANG EMAS DITEMUKAN] {best_sym} memicu Sinyal Beli Momentum (RSI turun ke {best_rsi:.2f})!"
                )
                print(Fore.GREEN + f" -> {best_sig.reason}")
                self.execute_buy(symbol=best_sym, current_price=best_price)
            else:
                print(
                    f"[{timestamp_str}] #{iteration} | Saldo: {self.current_balance:,.2f} USDT | "
                    f"[SCAN {self.config.timeframe}] {scan_str} | Status: MENUNGGU"
                )

    def start(self):
        """Memulai loop pemantauan pasar secara berulang."""
        self.config.print_summary()
        self.initialize()

        self.is_running = True
        iteration = 1
        print(
            Fore.CYAN + Style.BRIGHT
            + f"\nBot trading aktif berjalan. Memeriksa pasar setiap {self.config.poll_interval_seconds} detik."
        )
        print(Fore.CYAN + "Tekan Ctrl+C untuk menghentikan bot secara aman.\n")

        try:
            while self.is_running:
                self.run_iteration(iteration)
                iteration += 1
                time.sleep(self.config.poll_interval_seconds)
        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n\nSinyal penghentian (Ctrl+C) diterima. Menutup bot trading dengan aman...")
        finally:
            self.is_running = False
            print(Fore.GREEN + "Bot trading berhasil dihentikan.\n")
