# 🤖 Bot Trading Hybrid Advanced Prosumer - Berbasis Saringan Buku Besar

Selamat datang di repositori **Bot Trading Hybrid Advanced Prosumer**. Sistem ini dibangun dengan arsitektur dua lapis (Two-Layer Execution Engine) yang memadukan agresivitas pencarian tren masa lalu dengan ketatnya penyaringan aliran uang riil (*Smart Money*) saat ini menggunakan prinsip **Buku Besar Digital**.

Sistem ini dirancang khusus agar dapat berjalan ringan, stabil, dan nonstop 24/7 di perangkat Android menggunakan **Termux**.

---

## 🧠 Filosofi & Logika Kerja Sistem

Kebanyakan bot trading ritel mengalami kegagalan (*Margin Call*) karena melakukan optimasi berlebihan (*overfitting*) pada data grafik masa lalu tanpa memedulikan realitas volume bandar detik ini. Sistem ini memecah tugas tersebut menjadi dua entitas mandiri yang saling berkomunikasi:

### 1. Bot 1: Re-Optimizer (Masa Lalu / Taktis)
* Bekerja setiap 1 jam melakukan simulasi *backtesting brute-force* kasar pada data historis 48 jam terakhir.
* Mencari kombinasi parameter indikator terbaik yang menghasilkan peningkatan ekuitas terbesar (*Best-Fitting Equity*).
* Menulis taktik terbaik tersebut ke dalam file `setting_terbaik.json`.

### 2. Bot 2: Scanner & Executor (Saat Ini / Buku Besar)
* **Auto-Liquidity Scanner**: Memindai seluruh bursa secara dinamis untuk mencari **10 koin teraktif** dengan volume transaksi (omset dolar) terbesar 24 jam terakhir. Ini mencegah bot terjebak pada koin mati yang *sideways*.
* **Filter Buku Besar**: Sinyal agresif dari grafik masa lalu **wajib divalidasi** oleh data API detik ini juga. Bot akan memeriksa pertumbuhan kontrak (`Open Interest Growth`) dan biaya pendanaan (`Funding Rate`). Jika grafik menyuruh masuk posisi tetapi Buku Besar mendeteksi volume uang asli kosong, **order akan langsung dibatalkan (Anti-Fakeout)**.

---

## 📊 Manajemen Risiko Dinamis (Matriks 5% - 15%)

Sistem ini secara otomatis mengubah porsi modal yang dipertaruhkan per transaksi (`RISK_PER_TRADE`) berdasarkan hasil proyeksi profit bulanan dari hasil *backtest* Bot 1 guna menghindari kebangkrutan:

1. **🟢 ZONA AMAN (Profit < 5%)** -> Risiko rendah. Pasar stabil dan organik. Bot merisikokan **2.0%** dari total modal per transaksi.
2. **🟡 ZONA WASPADA (Profit 5% - 15%)** -> Risiko sedang. Volatilitas meningkat. Bot memotong risiko menjadi **1.0%** dari total modal.
3. **🔴 ZONA BAHAYA MC (Profit > 15%)** -> Risiko sangat tinggi. Pasar rawan manipulasi. Rem darurat aktif otomatis, risiko dipotong ketat menjadi hanya **0.5%** modal demi melindungi akun dari *Margin Call* (MC).

---

## 🛠️ Panduan Instalasi di Termux (Android)

Jalankan perintah berikut satu per satu di aplikasi Termux Anda untuk mempersiapkan lingkungan server:

```bash
# Update package dan install dependensi sistem
pkg update && pkg upgrade -y
pkg install git python clang make -y

# Clone repositori ini
git clone https://github.com/kangrisuk-id/zf.bot.crypto/
cd zf.bot.crypto

# Install seluruh library Python yang dibutuhkan
pip install -r requirements.txt
```

### 🔐 Pengaturan File Rahasia (`.env`)
Buat file konfigurasi rahasia untuk menyimpan API Key dan bot Telegram Anda:
```bash
nano .env
```
Isi dengan format berikut (jangan bagikan file ini ke siapa pun):
```text
BYBIT_API_KEY=api_key_bursa_anda
BYBIT_SECRET=secret_key_bursa_anda
TELEGRAM_TOKEN=token_bot_telegram_anda
TELEGRAM_CHAT_ID=id_chat_telegram_anda
```

---

## 🚀 Cara Menjalankan Bot 24/7

Gunakan **Tmux** agar bot tetap berjalan di latar belakang Android meskipun layar HP Anda mati atau terkunci:

```bash
# 1. Pastikan CPU HP tetap terjaga
termux-wake-lock

# 2. Jalankan Bot 1 (Optimizer) di jendela terpisah
tmux new -s bot1_opt
python bot_optimizer.py
# (Tekan Ctrl + B, lalu lepas, kemudian tekan D untuk keluar layar)

# 3. Jalankan Bot 2 (Eksekutor & Buku Besar) di jendela kedua
tmux new -s bot2_exe
python bot_executor.py
# (Tekan Ctrl + B, lalu lepas, kemudian tekan D untuk keluar layar)
```

### 📈 Memantau Raport Trading
Setiap transaksi yang berhasil ditutup oleh fitur **Dynamic Trailing Stop** akan dicatat secara otomatis dalam sistem akuntansi lokal. Untuk mengecek ringkasan *Win Rate* dan akumulasi profit/loss dolar Anda, ketik:
```bash
cat log_performa.txt
```
