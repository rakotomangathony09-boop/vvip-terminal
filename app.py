import os
import time
import pandas as pd
import pandas_ta as ta
import telebot
import asyncio
from threading import Thread
from datetime import datetime
from flask import Flask
from deriv_api import DerivAPI

# --- CONFIGURATION ---
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
TG_TOKEN = os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
APP_ID = os.getenv("APP_ID", "1089")

# Initialisation Flask pour Render
app = Flask(__name__)
bot_tg = None

if TG_TOKEN:
    bot_tg = telebot.TeleBot(TG_TOKEN)

class SniperSystem:
    def __init__(self):
        self.symbols = ["frxXAUUSD", "BOOM1000", "BOOM500", "CRASH1000", "CRASH500"]
        self.data_frames = {s: pd.DataFrame() for s in self.symbols}
        self.last_signal_time = {s: 0 for s in self.symbols}

    def is_market_open(self, symbol):
        """Gestion de la fermeture du Gold le week-end (UTC)"""
        if "XAU" in symbol:
            now = datetime.utcnow()
            weekday = now.weekday() 
            if (weekday == 4 and now.hour >= 21) or weekday == 5 or (weekday == 6 and now.hour < 22):
                return False
        return True

    def analyze_smc(self, df, symbol):
        if len(df) < 50: return None
        last = df.iloc[-1]
        df['rsi'] = ta.rsi(df['close'], length=14)
        rsi = df['rsi'].iloc[-1]
        
        candle_range = last['high'] - last['low']
        body_size = abs(last['close'] - last['open'])
        wick_percent = ((candle_range - body_size) / candle_range) if candle_range > 0 else 0
        
        low_zone = df['low'].iloc[-30:-1].min()
        high_zone = df['high'].iloc[-30:-1].max()

        if last['low'] < low_zone and wick_percent > 0.55 and rsi < 25:
            return {"type": "BUY 🔵", "price": last['close']}
        if last['high'] > high_zone and wick_percent > 0.55 and rsi > 75:
            return {"type": "SELL 🔴", "price": last['close']}
        return None

system = SniperSystem()

async def deriv_worker():
    api = DerivAPI(app_id=APP_ID)
    await api.authorize(DERIV_TOKEN)
    
    async def subscribe(symbol):
        while True:
            try:
                if not system.is_market_open(symbol):
                    await asyncio.sleep(3600)
                    continue
                
                sub = await api.subscribe({'ohlc': symbol, 'granularity': 60})
                async for msg in sub:
                    o = msg['ohlc']
                    new_c = {'epoch': o['open_time'], 'close': float(o['close']), 'high': float(o['high']), 'low': float(o['low']), 'open': float(o['open'])}
                    
                    df = system.data_frames[symbol]
                    system.data_frames[symbol] = pd.concat([df, pd.DataFrame([new_c])], ignore_index=True).tail(100)
                    
                    setup = system.analyze_smc(system.data_frames[symbol], symbol)
                    if setup and (time.time() - system.last_signal_time[symbol] > 300):
                        msg_text = f"🎯 **VVIP SIGNAL: {symbol}**\n🔥 Ordre: {setup['type']}\n📍 Prix: {setup['price']}"
                        if bot_tg:
                            bot_tg.send_message(TG_CHAT_ID, msg_text, parse_mode="Markdown")
                        system.last_signal_time[symbol] = time.time()
            except:
                await asyncio.sleep(10)

    await asyncio.gather(*(subscribe(s) for s in system.symbols))

@app.route('/')
def health():
    return "Mc ANTHONIO VVIP TERMINAL ONLINE", 200

if __name__ == "__main__":
    # Ce bloc n'est utilisé qu'en local, Render utilise Gunicorn
    Thread(target=lambda: asyncio.run(deriv_worker()), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
