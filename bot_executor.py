import ccxt
import pandas as pd
import numpy as np
import json
import time
import os
import requests

# Load library pembaca file .env manual agar ringan di Termux
def load_env():
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    env_vars[k] = v
    return env_vars

env = load_env()

# ==============================================================================
# SAKELAR UTAMA SIKLUS (Ubah ke 'LIVE' untuk trading asli)
# ==============================================================================
MODE = 'PAPER' 

exchange = ccxt.bybit({
    'apiKey': env.get('BYBIT_API_KEY', ''),
    'secret': env.get('BYBIT_SECRET', ''),
    'options': {'defaultType': 'linear'}, 'enableRateLimit': True
})

LEVERAGE = 5
TELEGRAM_TOKEN = env.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = env.get('TELEGRAM_CHAT_ID', '')
PERFORMANCE_FILE = "log_performa.txt"

# Dompet Buku Besar Virtual (Paper Trading)
PAPER_BALANCE = 10000.0  
paper_positions = {} # Menyimpan banyak posisi aktif koin ter-scan

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
    except: pass

# ==============================================================================
# AUTOMATIC LIQUIDITY SCANNER (10 Koin Tren & Transaksi Terbesar)
# ==============================================================================
def dapatkan_10_market_teraktif():
    try:
        tickers = exchange.fetch_tickers()
        list_koin = []
        for symbol, data in tickers.items():
            if '/USDT' in symbol and data.get('quoteVolume'):
                list_koin.append({'symbol': symbol, 'volume_24h': float(data['quoteVolume'])})
        koin_terurut = sorted(list_koin, key=lambda x: x['volume_24h'], reverse=True)
        return [koin['symbol'] for koin in koin_terurut[:10]]
    except:
        return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT']

# ==============================================================================
# PROFILER RISIKO DINAMIS (Aturan 5% - 15% Anda)
# ==============================================================================
def hitung_dynamic_risk(equity_multiplier):
    profit_pct = (equity_multiplier - 1.0) * 100
    if profit_pct < 5.0: return 0.02, "🟢 RISIKO RENDAH (<5%)"
    elif 5.0 <= profit_pct <= 15.0: return 0.01, "🟡 RISIKO SEDANG (5%-15%)"
    else: return 0.005, "🔴 RISIKO TINGGI (>15% - REM MC AKTIF)"

# ==============================================================================
# SISTEM PEMBUKUAN STATISTIK RAPORT
# ==============================================================================
def catat_raport_keuntungan(pnl_amount):
    wins, losses, total_pnl = 0, 0, 0.0
    if os.path.exists(PERFORMANCE_FILE):
        with open(PERFORMANCE_FILE, "r") as f:
            for line in f:
                if "SUMMARY|" in line:
                    parts = line.strip().split("|")
                    wins, losses, total_pnl = int(parts[1]), int(parts[2]), float(parts[3])
    if pnl_amount > 0: wins += 1
    else: losses += 1
    total_pnl += pnl_amount
    wr = (wins / (wins + losses)) * 100
    
    with open(PERFORMANCE_FILE, "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] P&L: ${pnl_amount:.2f}\n")
        f.write(f"SUMMARY|{wins}|{losses}|{total_pnl:.2f}|{wr:.2f}\n")
        
    send_telegram(f"📊 *RAPORT TRADING DIKUNCI*\n✅ Win: {wins}x | ❌ Loss: {losses}x\n🎯 Win Rate: {wr:.2f}%\n💰 Total Akumulasi P&L: ${total_pnl:.2f}")

# ==============================================================================
# TRAILING STOP & EXECUTION CORE
# ==============================================================================
def kelola_trailing_stop_dan_exit(symbol, current_price):
    global PAPER_BALANCE, paper_positions
    if MODE == 'PAPER' and symbol in paper_positions:
        pos = paper_positions[symbol]
        if pos['side'] == 'LONG':
            if current_price > pos['max_p']: pos['max_p'] = current_price
            if (pos['max_p'] - pos['entry']) / pos['entry'] >= 0.01:
                if current_price <= pos['max_p'] * 0.995:
                    pnl = (current_price - pos['entry']) * pos['qty']
                    PAPER_BALANCE += pnl
                    catat_raport_keuntungan(pnl)
                    del paper_positions[symbol]
        elif pos['side'] == 'SHORT':
            if current_price < pos['min_p']: pos['min_p'] = current_price
            if (pos['entry'] - pos['min_p']) / pos['entry'] >= 0.01:
                if current_price >= pos['min_p'] * 1.005:
                    pnl = (pos['entry'] - current_price) * pos['qty']
                    PAPER_BALANCE += pnl
                    catat_raport_keuntungan(pnl)
                    del paper_positions[symbol]

def jalankan_analisa_buku_besar(symbol, p_cepat, p_lambat, allowed_risk):
    global PAPER_BALANCE, paper_positions
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=30)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ma_cepat'] = df['close'].rolling(window=p_cepat).mean()
        df['ma_lambat'] = df['close'].rolling(window=p_lambat).mean()
        
        current_p = df['close'].iloc[-1]
        kelola_trailing_stop_dan_exit(symbol, current_p)
        
        # Cek apakah sudah punya posisi di koin ini
        if MODE == 'PAPER' and symbol in paper_positions: return
        
        # Sinyal Agresif Grafik (Lapisan 1)
        sinyal = "NONE"
        if df['ma_cepat'].iloc[-1] > df['ma_lambat'].iloc[-1]: sinyal = "LONG"
        elif df['ma_cepat'].iloc[-1] < df['ma_lambat'].iloc[-1]: sinyal = "SHORT"
        
        if sinyal == "NONE": return
        
        # Saringan Buku Besar API Detik Ini (Lapisan 2)
        fr = exchange.fetch_funding_rate(symbol)['fundingRate']
        market_meta = exchange.market(symbol)
        oi_res = exchange.publicLinearGetOpenInterest({"symbol": market_meta['id'], "period": "1h", "limit": 2})
        oi_list = oi_res['result']['list']
        oi_growth = ((float(oi_list[0]['openInterest']) - float(oi_list[1]['openInterest'])) / float(oi_list[1]['openInterest'])) * 100
        
        # Aturan Buku Besar: Cegah order jika aliran uang retail kosong
        if oi_growth > 1.5:
            sl_dist = current_p * 0.015
            bal = PAPER_BALANCE if MODE == 'PAPER' else float(exchange.fetch_balance()['USDT']['total'])
            qty = (bal * allowed_risk) / sl_dist
            
            if sinyal == "LONG" and fr > 0.0001:
                send_telegram(f"✅ *OP VALID LONG*: {symbol}\n🎯 Price: ${current_p} | Qty: {qty:.3f}")
                if MODE == 'PAPER':
                    paper_positions[symbol] = {'side':'LONG', 'qty':qty, 'entry':current_p, 'max_p':current_p, 'min_p':current_p}
            elif sinyal == "SHORT" and fr < -0.0001:
                send_telegram(f"✅ *OP VALID SHORT*: {symbol}\n🎯 Price: ${current_p} | Qty: {qty:.3f}")
                if MODE == 'PAPER':
                    paper_positions[symbol] = {'side':'SHORT', 'qty':qty, 'entry':current_p, 'max_p':current_p, 'min_p':current_p}
    except:
        pass

if __name__ == '__main__':
    print("🤖 Bot 2 Eksekutor 3-in-1 Aktif di Termux...")
    while True:
        try:
            if os.path.exists('setting_terbaik.json'):
                with open('setting_terbaik.json', 'r') as f: config = json.load(f)
            else:
                config = {'param_cepat': 5, 'param_lambat': 20, 'best_equity_multiplier': 1.02}
                
            allowed_risk, zona = hitung_dynamic_risk(config.get('best_equity_multiplier', 1.02))
            koin_aktif = dapatkan_10_market_teraktif()
            
            for koin in koin_aktif:
                jalankan_analisa_buku_besar(koin, config['param_cepat'], config['param_lambat'], allowed_risk)
                time.sleep(0.5) # Jeda anti-banned rate limit bursa
                
            time.sleep(300) # Scan berkala per 5 menit
        except Exception as e:
            time.sleep(10)
  
