# Binance Spot Testnet & Mainnet Trading Bot with AI Machine Learning

Bot trading cryptocurrency otomatis berbasis Python yang dibangun secara modular untuk bursa **Binance Spot** (mendukung Testnet & Mainnet) menggunakan library **CCXT**. Dilengkapi dengan pemindaian multi-market, strategi **RSI Momentum Dinamis**, **MA200 Trend Filter**, serta model **AI Machine Learning (Predictive Signal Filter)**. Bot juga terintegrasi penuh dengan sistem **manajemen risiko** (alokasi modal maksimal 10% saldo dan Take Profit / Stop Loss dinamis).

---

## 🌟 Fitur-Fitur Terkini (Update Terbaru)

1. **Multi-Market Scanner (Watchlist)**
   Bot tidak lagi mengandalkan satu koin. Cukup daftarkan koin-koin favorit Anda di variabel `WATCHLIST` dalam file `.env` (misal: `BNB/USDT, SOL/USDT, ADA/USDT`), dan bot akan memindai semuanya secara bergantian mencari peluang terbaik.
   
2. **Strategi RSI Momentum Dinamis (Bukan Sekadar Oversold)**
   Alih-alih menggunakan batas kaku seperti RSI < 30 (Oversold), bot kini membaca momentum:
   - **Sinyal Beli**: Terpicu jika nilai RSI turun minimal 3 poin dari *candle* sebelumnya (menandakan momentum *dip* atau penurunan tajam sesaat).
   - **Sinyal Jual (Take Profit)**: Terpicu secara dinamis ketika RSI mulai naik kembali, mengikuti pantulan harga yang sesungguhnya.

3. **MA200 Trend Filter (Proteksi Downtrend)**
   Sinyal beli RSI sebaik apapun akan diabaikan (dibatalkan) jika harga koin saat itu berada **di bawah garis MA200 (Moving Average 200)**. Ini adalah proteksi solid untuk mencegah bot menangkap pisau jatuh (*falling knife*) saat pasar sedang tren turun panjang.

4. **Kecerdasan Buatan (AI Hybrid Strategy)**
   Sinyal momentum RSI dan tren MA200 dapat divalidasi ganda oleh model Machine Learning yang telah dilatih secara khusus memprediksi probabilitas kenaikan harga. Sinyal hanya lolos jika AI mendeteksi persentase kesuksesan yang tinggi.

---

## 📁 Struktur Direktori Proyek

```text
binance_trading_bot/
├── .env                          # Konfigurasi aktif (API keys, watchlist, parameter risiko, AI)
├── main.py                       # Titik masuk utama untuk menjalankan bot trading
├── download_historical_data.py   # Skrip pengunduh data historis untuk training AI
├── train_ai_model.py             # Skrip pelatihan model AI (GradientBoosting / RandomForest)
├── check_balance.py              # Skrip untuk memeriksa saldo tunai USDT & altcoin saat ini
├── data/                         # Folder penyimpanan dataset historis (.csv)
├── models/                       # Folder artefak model AI terlatih (.joblib)
├── src/                          # Modul inti bot (Modular Architecture)
│   ├── config.py                 # Pembaca & validator .env terstruktur
│   ├── exchange.py               # Client CCXT Binance
│   ├── fetcher.py                # Pembaca Ticker & Candlestick OHLCV (limit 210 candle)
│   ├── features.py               # Ekstraksi 18 indikator teknikal untuk Machine Learning
│   ├── strategy.py               # Logika RSI Momentum Dinamis + MA200 Trend Filter
│   ├── ai_strategy.py            # Strategi Hybrid (Momentum RSI + MA200 + AI Probability Filter)
│   ├── risk.py                   # Aturan 10% Saldo USDT, Target TP & SL
│   └── bot.py                    # Koordinator alur trading, multi-market scanner & monitoring
```

---

## 🧠 Cara Kerja Model AI & Jadwal Retraining

### Mode Bekerja vs Belajar
- **Saat Bot Berjalan (Live Trading):** Bot secara **otomatis & real-time** menarik data *candle* terbaru dari Binance setiap 5 detik (sesuai `POLL_INTERVAL_SECONDS`). Model AI akan memproses grafik detik itu juga untuk membuat prediksi. AI *selalu up-to-date* terhadap kondisi market saat itu.
- **Saat Pelatihan (Retraining):** "Ingatan" pola pasar AI didapat dari file data historis (`data/historical_candles_15m.csv`). Data riwayat ini statis. Agar AI tetap peka terhadap tren kripto terkini, **sangat disarankan untuk melatih ulang model secara manual (menjalankan `download_historical_data.py` dilanjutkan `train_ai_model.py`) setidaknya 1 atau 2 minggu sekali.**

---

## 🛡️ Aturan Manajemen Risiko & Modal (Mainnet)

1. **Batas Alokasi Modal Maksimal (10% Saldo USDT)**:
   - Pembelian dibatasi sesuai konfigurasi `MAX_BALANCE_RISK_PERCENT` di file `.env`. 
   - Nilai *default* adalah `10.0` (Artinya bot hanya memakai 10% dari uang tunai/USDT untuk sekali beli).
2. **Kebutuhan Minimum Saldo untuk Mainnet**:
   - Limit transaksi terendah di Binance Spot (Notional Limit) umumnya berkisar **$5 - $10 USD**.
   - Jika Anda membatasi bot hanya 10% per transaksi, maka **saldo total minimal yang dianjurkan untuk Mainnet adalah $100 USDT**. (Sehingga 10% dari $100 = $10, aman melewati limit bursa).
   - *Catatan: Jika Anda hanya ingin modal $20 USDT, Anda harus menaikkan limit risiko di `.env` menjadi misal 50% atau 100%.*

---

## 🚀 Panduan Penggunaan Lengkap

### 1. Persiapan Awal
Pasang dependensi Python yang dibutuhkan:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Mengatur Watchlist Koin & Setelan Utama
Buka file `.env` dan tambahkan koin-koin favorit Anda:
```env
WATCHLIST=BNB/USDT,SOL/USDT,XRP/USDT,ADA/USDT,DOGE/USDT,ETH/USDT,BTC/USDT
STRATEGY_TYPE=HYBRID   # Pilihan: RSI atau HYBRID atau AI_ONLY
IS_TESTNET=True        # Ubah ke False jika sudah siap pakai uang sungguhan (Mainnet)
DRY_RUN=False
```

### 3. Melatih Model AI (Wajib Lakukan Secara Berkala)
Unduh data pasar terbaru lalu latih model AI-nya:
```bash
./venv/bin/python download_historical_data.py --candles 5000
./venv/bin/python train_ai_model.py
```

### 4. Menjalankan Bot Trading
Nyalakan mesin utama pencetak cuan:
```bash
./venv/bin/python main.py
```
> Tekan `Ctrl + C` kapan saja untuk menghentikan bot secara aman (*graceful shutdown*).
