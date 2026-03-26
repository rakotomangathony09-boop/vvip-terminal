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

# --- CONTENU PSYCHOLOGIQUE ---
MOTIVATIONS_OPEN = [
    "Attends le Sweep, confirme le BOS. Sois un sniper, pas un parieur.",
    "La liquidité est le carburant du marché. Ne sois pas la liquidité, suis les banques.",
    "Discipline : Pas de bougie de rejet = Pas de trade."
]
MOTIVATIONS_CLOSE = [
    "Session terminée. Ton mental est ton plus gros actif, protège-le.",
    "Le marché ne s'arrête jamais, mais toi si. Repose-toi.",
    "La victoire est d'avoir respecté la stratégie, peu importe le gain."
]

class SniperSystem:
    def __init__(self):
        self.session_active = True
        self.daily_news = []
        self.symbols = ["BOOM1000", "BOOM500", "BOOM300", "CRASH1000", "CRASH500", "CRASH300"]
        self.data_frames = {s: pd.DataFrame() for s in self.symbols}
        
        # Stats pour Rapport 3h
        self.ticks_processed = 0
        self.sweeps_detected = 0
        self.signals_sent = 0
        self.last_signal_time = {s: 0 for s in self.symbols}

    def sync_news(self):
        """Récupère les news USD High Impact"""
        if not FINNHUB_KEY: return
        today = datetime.utcnow().strftime('%Y-%m-%d')
        url = f"https://finnhub.io/api/v1/calendar/economic?from={today}&to={today}&token={FINNHUB_KEY}"
        try:
            res = requests.get(url).json()
            self.daily_news = [n for n in res.get('economicCalendar', []) 
                              if n['country'] == 'US' and n['impact'] == 'high']
            return True
        except: return False

    def analyze_smc(self, df, symbol):
        """Logique Sniper SMC : Sweep + Rejet + RSI"""
        if len(df) < 40: return None
        
        last = df.iloc[-1]
        df['rsi'] = ta.rsi(df['close'], length=14)
        rsi = df['rsi'].iloc[-1]
        
        # Mèche de rejet (Wick)
        candle_range = last['high'] - last['low']
        body_size = abs(last['close'] - last['open'])
        wick_percent = ((candle_range - body_size) / candle_range) if candle_range > 0 else 0
        
        # Liquidité (30 bougies)
        low_zone = df['low'].iloc[-30:-1].min()
        high_zone = df['high'].iloc[-30:-1].max()
        
        is_boom = "BOOM" in symbol
        is_crash = "CRASH" in symbol

        # Detection Sweep
        if is_boom and last['low'] < low_zone:
            self.sweeps_detected += 1
            if wick_percent > 0.5 and rsi < 28:
                return {"type": "🚀 SNIPER BUY", "entry": last['close'], "sl": last['low'] - 1.5}
        
        if is_crash and last['high'] > high_zone:
            self.sweeps_detected += 1
            if wick_percent > 0.5 and rsi > 72:
                return {"type": "📉 SNIPER SELL", "entry": last['close'], "sl": last['high'] + 1.5}
        
        return None

system = SniperSystem()

# --- ALERTES TELEGRAM ---

def send_signal(symbol, setup):
    msg = (f"🎯 **SIGNAL SNIPER SMC**\n\n"
           f"🔥 **ORDRE : {setup['type']}**\n"
           f"📈 Actif : `{symbol}`\n"
           f"📍 ENTRÉE : `{setup['entry']:.2f}`\n"
           f"🛡️ STOP LOSS : `{setup['sl']:.2f}`\n"
           f"✅ *Confirmation : Rejection Candle + RSI validés*")
    bot_tg.send_message(TG_CHAT_ID, msg, parse_mode="Markdown")
    system.signals_sent += 1

def send_report():
    now = datetime.utcnow().strftime('%H:%M')
    msg = (f"📊 **RAPPORT D'ACTIVITÉ (3H)**\n"
           f"🕒 Heure : `{now} UTC`\n\n"
           f"🔢 Ticks traités : `{system.ticks_processed}`\n"
           f"🔎 Sweeps détectés : `{system.sweeps_detected}`\n"
           f"✅ Signaux validés : `{system.signals_sent}`\n\n"
           f"🤖 *Scan SMC en cours...*")
    bot_tg.send_message(TG_CHAT_ID, msg, parse_mode="Markdown")
    system.ticks_processed, system.sweeps_detected, system.signals_sent = 0, 0, 0

# --- BOUCLES DE TRAVAIL ---

async def deriv_worker():
    api = DerivAPI(app_id=APP_ID)
    await api.authorize(DERIV_TOKEN)
    
    async def subscribe_symbol(symbol):
        # Historique
        hist = await api.ticks_history({'ticks_history': symbol, 'count': 100, 'end': 'latest', 'style': 'candles', 'granularity': 60})
        system.data_frames[symbol] = pd.DataFrame(hist['candles'])
        
        # Stream
        sub = await api.subscribe({'ohlc': symbol, 'granularity': 60})
        async for msg in sub:
            if not system.session_active: continue
            
            o = msg['ohlc']
            system.ticks_processed += 1
            new_c = {'epoch': o['open_time'], 'open': float(o['open']), 'high': float(o['high']), 'low': float(o['low']), 'close': float(o['close'])}
            
            df = system.data_frames[symbol]
            if not df.empty and new_c['epoch'] == df.iloc[-1]['epoch']:
                df.iloc[-1] = new_c
            else:
                df = pd.concat([df, pd.DataFrame([new_c])], ignore_index=True)
            
            system.data_frames[symbol] = df.tail(100)
            
            # Analyse Sniper
            setup = system.analyze_smc(system.data_frames[symbol], symbol)
            if setup:
                now = time.time()
                if now - system.last_signal_time[symbol] > 180:
                    send_signal(symbol, setup)
                    system.last_signal_time[symbol] = now

    await asyncio.gather(*(subscribe_symbol(s) for s in system.symbols))

def scheduler_loop():
    for h in ["09:00", "12:00", "15:00", "18:00"]:
        schedule.every().day.at(h).do(send_report)
    
    schedule.every().day.at("06:00").do(lambda: [setattr(system, 'session_active', True), bot_tg.send_message(TG_CHAT_ID, f"🌅 **OUVERTURE SESSION**\n\n💡 `{random.choice(MOTIVATIONS_OPEN)}`")])
    schedule.every().day.at("21:00").do(lambda: [setattr(system, 'session_active', False), bot_tg.send_message(TG_CHAT_ID, f"🌙 **CLÔTURE SESSION**\n\n💤 `{random.choice(MOTIVATIONS_CLOSE)}`")])
    
    while True:
        schedule.run_pending()
        time.sleep(30)

@app.route('/')
def health(): return "SYSTEM OPERATIONAL", 200

if __name__ == "__main__":
    # Démarrage
    bot_tg.send_message(TG_CHAT_ID, "🚀 **TERMINAL SNIPER SMC DÉPLOYÉ**\n*(Synchronisation MT5 Live)*")
    system.sync_news()
    
    Thread(target=scheduler_loop, daemon=True).start()
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    
    asyncio.run(deriv_worker())
