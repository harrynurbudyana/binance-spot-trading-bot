# Binance Spot Testnet Modular Crypto Trading Bot with AI Machine Learning

Bot trading cryptocurrency otomatis berbasis Python yang dibangun secara modular untuk bursa **Binance Spot Testnet** menggunakan library **CCXT**, dilengkapi dengan strategi **RSI** dan model **AI Machine Learning (Predictive Signal Filter)**, serta sistem **manajemen risiko terintegrasi** (pembatasan alokasi modal maksimal 10% saldo dan Stop Loss statis 2%).

---

## 📁 Struktur Direktori Proyek

```text
binance_trading_bot/
├── .env                          # Konfigurasi aktif (API keys, parameter bot, risiko, AI)
├── .env.example                  # Template konfigurasi environment
├── requirements.txt              # Daftar dependensi Python (ccxt, pandas, scikit-learn, joblib)
├── test_connection.py            # Skrip pengujian 8 komponen (koneksi, data, AI, saldo)
├── main.py                       # Titik masuk utama untuk menjalankan bot trading
├── download_historical_data.py   # Skrip pengunduh ribuan data lilin historis dari Binance
├── train_ai_model.py             # Skrip pelatihan model AI (GradientBoosting / RandomForest)
├── README.md                     # Dokumentasi lengkap proyek
├── data/
│   └── historical_candles_15m.csv # Dataset historis 5,000 lilin 15m untuk training
├── models/
│   └── ai_trading_model.joblib   # Artefak model AI terlatih beserta metadata & scaler
├── src/                          # Modul inti bot (Modular Architecture)
│   ├── __init__.py               # Inisialisasi package src
│   ├── config.py                 # [BotConfig] Pembaca & validator .env terstruktur
│   ├── exchange.py               # [BinanceExchangeClient] Client CCXT Binance Spot Testnet
│   ├── fetcher.py                # [PriceFetcher] Pembaca Ticker, Candlestick OHLCV, Orderbook
│   ├── features.py               # [FeatureEngineering] Ekstraksi 18 indikator teknikal untuk AI
│   ├── strategy.py               # [RSIStrategy] Logika RSI 15m (Beli jika RSI < 30)
│   ├── ai_strategy.py            # [AIPredictiveStrategy] Strategi Hybrid (RSI + AI Filter)
│   ├── risk.py                   # [RiskManager] Aturan 10% Saldo USDT & Stop Loss Statis 2%
│   └── bot.py                    # [CryptoTradingBot] Koordinator alur trading & monitoring
└── tests/
    └── test_modules.py           # Unit tests (RSI, Risk Management, AI Feature Extraction)
```

---

## 🧠 Modul AI Machine Learning

### 1. Rekayasa Fitur (Feature Engineering)
Modul [src/features.py](file:///home/harry/.gemini/antigravity-ide/scratch/binance_trading_bot/src/features.py) mengekstrak 18 fitur teknikal prediktif dari data pasar:
- **Momentum Pengembalian**: `ret_1`, `ret_3`, `ret_5`
- **Osilator**: RSI-14, RSI-7, RSI Momentum Diff
- **Moving Average Spreads**: Rasio EMA (9/21, 21/50), Close vs EMA-21
- **MACD**: Normalized MACD Line & Histogram
- **Bollinger Bands**: `%B` (posisi pita) & `Bandwidth` (volatilitas)
- **Volatilitas**: Normalized ATR-14 (Average True Range)
- **Volume & Geometri Lilin**: Rasio Volume terhadap SMA-20, Volume Change, Rasio Body/Wick

### 2. Strategi Hybrid AI Filter ([src/ai_strategy.py](file:///home/harry/.gemini/antigravity-ide/scratch/binance_trading_bot/src/ai_strategy.py))
- **Alur Keputusan**:
  1. Lilin 15 menit diperiksa apakah terjadi kondisi Oversold (`RSI < 30`).
  2. Jika RSI < 30, **Model AI memprediksi probabilitas kenaikan harga** dalam 3 lilin (45 menit) ke depan tanpa menyentuh stop loss.
  3. **Hanya mengeksekusi BELI** jika probabilitas AI melampaui ambang keyakinan (`AI_CONFIDENCE_THRESHOLD`, misal 35%–40%).
  4. Jika RSI < 30 tetapi AI mendeteksi momentum melemah atau risiko penurunan tinggi, sinyal beli **otomatis dibatalkan** untuk melindungi modal dari *false breakout*.

---

## 🚀 Panduan Penggunaan Lengkap

### 1. Masuk ke Direktori Proyek
```bash
cd /home/harry/.gemini/antigravity-ide/scratch/binance_trading_bot
```

### 2. Aktifkan Virtual Environment & Pasang Dependensi
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Mengunduh Data Historis untuk AI
Unduh 5.000 data lilin historis 15 menit (~52 hari) dari Binance:
```bash
./venv/bin/python download_historical_data.py --candles 5000
```

### 4. Melatih (Train) Model AI
Latih model AI prediktif berbasis *Gradient Boosting*:
```bash
./venv/bin/python train_ai_model.py
```
> Model akan dievaluasi dengan *out-of-sample test set* dan disimpan otomatis ke `models/ai_trading_model.joblib`.

### 5. Menjalankan Uji Diagnostik Sistem (8 Komponen)
```bash
./venv/bin/python test_connection.py
```

### 6. Menjalankan Bot Trading
```bash
./venv/bin/python main.py
```
- Menekan `Ctrl + C` akan menghentikan bot secara aman (*graceful shutdown*).
- Secara default, bot berjalan dalam mode **`DRY_RUN=True`** (simulasi aman tanpa memotong saldo).
- Untuk mengirim order nyata ke bursa Binance Testnet, ubah baris di [.env](file:///home/harry/.gemini/antigravity-ide/scratch/binance_trading_bot/.env): `DRY_RUN=False`.

### 7. Menjalankan Unit Tests
```bash
./venv/bin/python -m unittest discover -s tests
```

---

## 🛡️ Aturan Manajemen Risiko
1. **Batas Alokasi Modal 10% Saldo**:
   - Pembelian dibatasi maksimal 10% dari saldo bebas USDT yang tersedia (`free_usdt * 0.10`).
   - Dilengkapi validasi *minimum notional* dan *minimum lot size* Binance.
2. **Stop Loss Statis 2%**:
   - Dipasang pada harga: $\text{Stop Loss} = \text{Entry Price} \times 0.98$.
   - Jika harga pasar menyentuh atau turun menembus level SL, bot seketika mengeksekusi order jual darurat (*cut loss*).
