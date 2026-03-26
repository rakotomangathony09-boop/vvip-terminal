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

# --- CONFIGURATION (Variables Render) ---
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FINNHUB_KEY = os.getenv("FINNHUB_KEY")
APP_ID = os.getenv("APP_ID", "1089")

bot_tg = telebot.TeleBot(TG_TOKEN)
app = Flask(__name__)

# --- PSYCHOLOGIE DU TRADER ---
MOTIVATIONS_OPEN = [
    "Attends le Sweep, confirme le BOS. Sois un sniper, pas un parieur.",
    "La liquidité est le carburant du marché. Ne sois pas la liquidité.",
    "Discipline : Pas de bougie de rejet = Pas de trade."
]
MOTIVATIONS_CLOSE = [
    "Session terminée. Déconnecte-toi. Protège ton capital mental.",
    "Le marché ne dort jamais, mais ton cerveau en a besoin.",
    "La victoire est d'avoir respecté le plan de trading."
]

class SniperSystem:
    def __init__(self):
        self.session_active = True
        self.daily_news = []
        # Actifs : Or (XAUUSD) + Boom & Crash
        self.symbols = ["frxXAUUSD", "BOOM1000", "BOOM500", "BOOM300", "CRASH1000", "CRASH500", "CRASH300"]
        self.data_frames = {s: pd.DataFrame() for s in self.symbols}
        
        # Statistiques
        self.ticks_processed = 0
        self.sweeps_detected = 0
        self.signals_sent = 0
        self.last_signal_time = {s: 0 for s in self.symbols}

    def sync_news(self):
        """News USD High Impact via Finnhub"""
        if not FINNHUB_KEY: return
        today = datetime.utcnow().strftime('%Y-%m-%d')
        url = f"https://finnhub.io/api/v1/calendar/economic?from={today}&to={today}&token={FINNHUB_KEY}"
        try:
            res = requests.get(url).json()
            self.daily_news = [n for n in res.get('economicCalendar', []) 
                              if n['country'] == 'US' and n['impact'] == 'high']
        except: pass

    def analyze_smc(self, df, symbol):
        """Stratégie SMC Sniper : Liquidity Sweep + Rejection + RSI"""
        if len(df) < 50: return None
        
        last = df.iloc[-1]
        df['rsi'] = ta.rsi(df['close'], length=14)
        rsi = df['rsi'].iloc[-1]
        
        # Analyse de la mèche (Rejet)
        candle_range = last['high'] - last['low']
        body_size = abs(last['close'] - last['open'])
        wick_percent = ((candle_range - body_size) / candle_range) if candle_range > 0 else 0
        
        # Zones de liquidité
        lookback = 50 if "XAU" in symbol else 30
        low_zone = df['low'].iloc[-lookback:-1].min()
        high_zone = df['high'].iloc[-lookback:-1].max()
        
        # --- LOGIQUE GOLD ---
        if "XAU" in symbol:
            if last['low'] < low_zone and wick_percent > 0.6 and rsi < 25:
                return {"type": "🏆 GOLD SNIPER BUY", "entry": last['close'], "sl": last['low'] - 0.55}
            if last['high'] > high_zone and wick_percent > 0.6 and rsi > 75:
                return {"type": "🏆 GOLD SNIPER SELL", "entry": last['close'], "sl": last['high'] + 0.55}

        # --- LOGIQUE BOOM & CRASH ---
        else:
            if "BOOM" in symbol and last['low'] < low_zone and wick_percent > 0.5 and rsi < 28:
                return {"type": "🚀 SPIKE BUY", "entry": last['close'], "sl": last['low'] - 1.5}
            if "CRASH" in symbol and last['high'] > high_zone and wick_percent > 0.5 and rsi > 72:
                return {"type": "📉 SPIKE SELL", "entry": last['close'], "sl": last['high'] + 1.5}
        
        return None

system = SniperSystem()

# --- ALERTES & RAPPORTS ---

def send_signal(symbol, setup):
    name = "GOLD (XAU/USD)" if "XAU" in symbol else symbol
    msg = (f"🎯 **SIGNAL SNIPER SMC**\n\n"
           f"🔥 **ORDRE : {setup['type']}**\n"
           f"📈 Actif : `{name}`\n"
           f"📍 **ENTRÉE :** `{setup['entry']:.2f}`\n"
           f"🛡️ **STOP LOSS :** `{setup['sl']:.2f}`\n\n"
           f"✅ *Confirmation : Sniper Rejection validé*")
    bot_tg.send_message(TG_CHAT_ID, msg, parse_mode="Markdown")
    system.signals_sent += 1

def send_report():
    msg = (f"📊 **RAPPORT D'ACTIVITÉ (3H)**\n"
           f"🕒 Heure : `{datetime.utcnow().strftime('%H:%M')} UTC`\n\n"
           f"🔢 Ticks : `{system.ticks_processed}`\n"
           f"🔎 Sweeps : `{system.sweeps_detected}`\n"
           f"✅ Signaux : `{system.signals_sent}`")
    bot_tg.send_message(TG_CHAT_ID, msg, parse_mode="Markdown")
    system.ticks_processed, system.sweeps_detected, system.signals_sent = 0, 0, 0

# --- BOUCLES DE TRAVAIL ---

async def deriv_worker():
    api = DerivAPI(app_id=APP_ID)
    await api.authorize(DERIV_TOKEN)
    
    async def subscribe(symbol):
        try:
            hist = await api.ticks_history({'ticks_history': symbol, 'count': 150, 'end': 'latest', 'style': 'candles', 'granularity': 60})
            system.data_frames[symbol] = pd.DataFrame(hist['candles'])
            
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
                
                system.data_frames[symbol] = df.tail(150)
                setup = system.analyze_smc(system.data_frames[symbol], symbol)
                if setup:
                    now = time.time()
                    if now - system.last_signal_time[symbol] > 300:
                        send_signal(symbol, setup)
                        system.last_signal_time[symbol] = now
        except:
            await asyncio.sleep(10)
            await subscribe(symbol)

    await asyncio.gather(*(subscribe(s) for s in system.symbols))

def scheduler_loop():
    for h in ["09:00", "12:00", "15:00", "18:00"]:
        schedule.every().day.at(h).do(send_report)
    schedule.every().day.at("06:00").do(lambda: [setattr(system, 'session_active', True), bot_tg.send_message(TG_CHAT_ID, f"🌅 **OUVERTURE**\n💡 `{random.choice(MOTIVATIONS_OPEN)}`")])
    schedule.every().day.at("21:00").do(lambda: [setattr(system, 'session_active', False), bot_tg.send_message(TG_CHAT_ID, f"🌙 **CLÔTURE**\n💤 `{random.choice(MOTIVATIONS_CLOSE)}`")])
    while True:
        schedule.run_pending()
        time.sleep(30)

@app.route('/')
def health(): return "SYSTEM ONLINE", 200

if __name__ == "__main__":
    try:
        bot_tg.send_message(TG_CHAT_ID, "🚀 **TERMINAL SNIPER SMC DÉPLOYÉ**\n*(Gold + Synthétiques)*")
        system.sync_news()
    except: pass
    
    Thread(target=scheduler_loop, daemon=True).start()
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    asyncio.run(deriv_worker())
