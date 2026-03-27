import os
import json
import time
import pandas as pd
import pandas_ta as ta
import telebot
import requests
import schedule
import random
import asyncio
from threading import Thread
from datetime import datetime
from flask import Flask
from deriv_api import DerivAPI

# --- CONFIGURATION (Variables d'environnement Render) ---
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FINNHUB_KEY = os.getenv("FINNHUB_KEY")
APP_ID = os.getenv("APP_ID", "1089")

bot_tg = telebot.TeleBot(TG_TOKEN)
app = Flask(__name__)

class SniperSystem:
    def __init__(self):
        self.session_active = True
        self.symbols = ["frxXAUUSD", "BOOM1000", "BOOM500", "BOOM300", "CRASH1000", "CRASH500", "CRASH300"]
        self.data_frames = {s: pd.DataFrame() for s in self.symbols}
        self.ticks_processed = 0
        self.sweeps_detected = 0
        self.signals_sent = 0
        self.last_signal_time = {s: 0 for s in self.symbols}

    def is_market_open(self, symbol):
        """Vérifie si le marché est ouvert (Sécurité Week-end pour l'Or)"""
        if "XAU" in symbol:
            now = datetime.utcnow()
            weekday = now.weekday()  # 4=Vendredi, 5=Samedi, 6=Dimanche
            hour = now.hour
            # Fermeture Vendredi 21h UTC - Réouverture Dimanche 22h UTC
            if (weekday == 4 and hour >= 21) or weekday == 5 or (weekday == 6 and hour < 22):
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
        
        lookback = 50 if "XAU" in symbol else 30
        low_zone = df['low'].iloc[-lookback:-1].min()
        high_zone = df['high'].iloc[-lookback:-1].max()

        # LOGIQUE SNIPER SMC (Sweep + Rejection)
        if last['low'] < low_zone and wick_percent > 0.55 and rsi < 25:
            self.sweeps_detected += 1
            label = "🏆 GOLD BUY" if "XAU" in symbol else "🚀 SPIKE BUY"
            return {"type": label, "entry": last['close'], "sl": last['low'] - (0.5 if "XAU" in symbol else 1.5)}

        if last['high'] > high_zone and wick_percent > 0.55 and rsi > 75:
            self.sweeps_detected += 1
            label = "🏆 GOLD SELL" if "XAU" in symbol else "📉 SPIKE SELL"
            return {"type": label, "entry": last['close'], "sl": last['high'] + (0.5 if "XAU" in symbol else 1.5)}
        
        return None

system = SniperSystem()

def send_signal(symbol, setup):
    name = "GOLD (XAU/USD)" if "XAU" in symbol else symbol
    msg = (f"🎯 **SIGNAL SNIPER SMC**\n\n"
           f"🔥 **ORDRE : {setup['type']}**\n"
           f"📈 Actif : `{name}`\n"
           f"📍 ENTRÉE : `{setup['entry']:.2f}`\n"
           f"🛡️ STOP LOSS : `{setup['sl']:.2f}`\n\n"
           f"✅ *Confirmation : Rejection validée*")
    bot_tg.send_message(TG_CHAT_ID, msg, parse_mode="Markdown")
    system.signals_sent += 1

async def deriv_worker():
    api = DerivAPI(app_id=APP_ID)
    await api.authorize(DERIV_TOKEN)
    
    async def subscribe(symbol):
        while True: # Boucle infinie pour auto-reconnexion
            try:
                if not system.is_market_open(symbol):
                    await asyncio.sleep(3600) # Attend 1h si marché fermé
                    continue

                hist = await api.ticks_history({'ticks_history': symbol, 'count': 150, 'style': 'candles', 'granularity': 60})
                system.data_frames[symbol] = pd.DataFrame(hist['candles'])
                sub = await api.subscribe({'ohlc': symbol, 'granularity': 60})
                
                async for msg in sub:
                    o = msg['ohlc']
                    system.ticks_processed += 1
                    new_c = {'epoch': o['open_time'], 'open': float(o['open']), 'high': float(o['high']), 'low': float(o['low']), 'close': float(o['close'])}
                    
                    df = system.data_frames[symbol]
                    if not df.empty and new_c['epoch'] == df.iloc[-1]['epoch']:
                        df.iloc[-1] = new_c
                    else:
                        df = pd.concat([df, pd.DataFrame([new_c])], ignore_index=True)
                    
                    system.data_frames[symbol] = df.tail(150)
                    setup = system.analyze_smc(system.data_frames[symbol], symbol)
                    
                    if setup:
                        now = time.time()
                        if now - system.last_signal_time[symbol] > 300: # Cooldown 5min
                            send_signal(symbol, setup)
                            system.last_signal_time[symbol] = now
            except Exception as e:
                print(f"Erreur sur {symbol}: {e}. Reconnexion dans 10s...")
                await asyncio.sleep(10)

    await asyncio.gather(*(subscribe(s) for s in system.symbols))

@app.route('/')
def health(): return "VVIP TERMINAL ONLINE", 200

if __name__ == "__main__":
    try:
        bot_tg.send_message(TG_CHAT_ID, "🚀 **VVIP TERMINAL DÉPLOYÉ**\n*(Gold + Synthétiques)*")
    except: pass
    # Lancement du serveur Web pour Render
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    # Lancement du bot Trading
    asyncio.run(deriv_worker())
