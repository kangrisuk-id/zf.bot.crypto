import ccxt
import pandas as pd
import numpy as np
import json
import time

exchange = ccxt.bybit({'options': {'defaultType': 'linear'}})
SYMBOL = 'BTC/USDT'

def hitung_backtest_kasar(df, periode_cepat, periode_lambat):
    df = df.copy()
    df['ma_cepat'] = df['close'].rolling(window=periode_cepat).mean()
    df['ma_lambat'] = df['close'].rolling(window=periode_lambat).mean()
    
    df['posisi'] = np.where(df['ma_cepat'] > df['ma_lambat'], 1, -1)
    df['return_market'] = df['close'].pct_change()
    df['return_strategi'] = df['posisi'].shift(1) * df['return_market']
    
    equity_akhir = (1 + df['return_strategi'].dropna()).prod()
    return equity_akhir

def optimasi_setelan_terbaik():
    print("🔄 Bot 1: Menarik data masa lalu untuk mencari settingan terbaik...")
    try:
        bars = exchange.fetch_ohlcv(SYMBOL, timeframe='15m', limit=192)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        best_equity = 0.0
        best_cepat = 5
        best_lambat = 20
        
        for cepat in range(3, 10):
            for lambat in range(12, 30):
                equity = hitung_backtest_kasar(df, cepat, lambat)
                if equity > best_equity:
                    best_equity = equity
                    best_cepat = cepat
                    best_lambat = lambat
                    
        setelan = {
            'last_update': time.strftime('%Y-%m-%d %H:%M:%S'),
            'best_equity_multiplier': round(best_equity, 4),
            'param_cepat': best_cepat,
            'param_lambat': best_lambat
        }
        
        with open('setting_terbaik.json', 'w') as f:
            json.dump(setelan, f, indent=4)
            
        print(f"✅ Bot 1 Berhasil! Setelan disimpan: MA-{best_cepat} vs MA-{best_lambat}")
    except Exception as e:
        print(f"Bot 1 Error: {e}")

if __name__ == '__main__':
    while True:
        optimasi_setelan_terbaik()
        time.sleep(3600)
  
