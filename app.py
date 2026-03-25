import os
import websocket
import json
import time
import telebot
import requests
import schedule
import random
from threading import Thread
from datetime import datetime
from flask import Flask

# --- CONFIGURATION SÉCURISÉE ---
API_TOKEN = os.getenv("DERIV_API_TOKEN")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
APP_ID = os.getenv("APP_ID", "1089")

bot_tg = telebot.TeleBot(TG_TOKEN)
app = Flask(__name__)

# --- CONTENU PSYCHOLOGIQUE ---
MOTIVATIONS_OPEN = [
    "Attends le Sweep, confirme le BOS, encaisse le profit. Sois un sniper, pas un parieur.",
    "La liquidité est le carburant du marché. Ne sois pas la liquidité, suis les banques.",
    "Discipline : Pas de bougie de rejet = Pas de trade. Respecte ton plan."
]
MOTIVATIONS_CLOSE = [
    "Session close. Déconnecte-toi. Ton mental est ton plus gros actif, protège-le.",
    "Le marché ne s'arrête jamais, mais toi si. Repose-toi pour être lucide demain.",
    "Peu importe tes gains, la victoire est d'avoir respecté la stratégie."
]

class SniperSystem:
    def __init__(self):
        self.session_active = False
        self.is_booted = False
        self.daily_news = []
        self.notified_news = []
        self.pre_alerted_setups = {} # Pour éviter le spam de pré-alertes
        
        # Statistiques pour Rapport 3h
        self.ticks_count = 0
        self.sweeps_detected = 0
        self.signals_sent = 0

    def sync_news(self):
        """Récupère les news USD High Impact"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        url = f"https://finnhub.io/api/v1/calendar/economic?from={today}&to={today}&token={FINNHUB_KEY}"
        try:
            res = requests.get(url).json()
            self.daily_news = [n for n in res.get('economicCalendar', []) 
                              if n['country'] == 'US' and n['impact'] == 'high']
            return True
        except: return False

    def is_gold_session(self):
        """Vérifie si on est en session Londres/NY (8h-21h UTC)"""
        now = datetime.utcnow()
        return 8 <= now.hour <= 21 and now.weekday() < 5

bot_logic = SniperSystem()

# --- SYSTÈME D'ALERTES ---

def send_pre_signal(symbol, side):
    """ Alerte T-2 min : Sweep détecté, en attente de Rejet """
    if symbol not in bot_logic.pre_alerted_setups:
        msg = (f"🔍 **PRÉ-ALERTE : SETUP EN COURS**\n\n"
               f"📈 Actif : `{symbol}`\n"
               f"⚡ Action : **{side} LIMIT**\n"
               f"🎯 État : Sweep détecté. En attente du Pullback + Rejet (~2 min).\n"
               f"📱 *Ouvrez votre MT5 et préparez l'actif.*")
        bot_tg.send_message(CHAT_ID, msg, parse_mode="Markdown")
        bot_logic.pre_alerted_setups[symbol] = time.time()

def send_final_signal(symbol, side, entry, sl, tp1, tp2):
    """ Signal final : Stratégie complète validée """
    msg = (f"🎯 **SIGNAL SNIPER SMC FINAL**\n\n"
           f"🔥 **ORDRE : {side}**\n"
           f"✅ *Confirmation : Sweep + BOS + Rejet OK*\n\n"
           f"📍 **ENTRÉE :** `{entry}`\n"
           f"🛡️ **STOP LOSS :** `{sl}` (Extrémité Sweep)\n"
           f"💰 **TP1 (50%) :** `{tp1}`\n"
           f"💎 **TP2 (Final) :** `{tp2}`\n\n"
           f"⚖️ *Gestion : Fermez 50% au TP1 et passez au BE.*")
    bot_tg.send_message(CHAT_ID, msg, parse_mode="Markdown")
    bot_logic.signals_sent += 1

# --- RAPPORTS ET AUTOMATISATION ---

def news_30min_checker():
    now = datetime.utcnow()
    for news in bot_logic.daily_news:
        n_time = datetime.strptime(news['time'], '%Y-%m-%d %H:%M:%S')
        diff = (n_time - now).total_seconds() / 60
        if 28 <= diff <= 31 and news['event'] not in bot_logic.notified_news:
            bot_tg.send_message(CHAT_ID, f"⚠️ **NEWS DANS 30 MIN**\n📢 Event : {news['event']}\n⚠️ Volatilité Gold attendue !")
            bot_logic.notified_news.append(news['event'])

def report_3h():
    msg = (f"📊 **RAPPORT D'ACTIVITÉ (3H)**\n\n"
           f"🔢 Ticks analysés : `{bot_logic.ticks_count}`\n"
           f"🔎 Sweeps détectés : `{bot_logic.sweeps_detected}`\n"
           f"✅ Signaux validés : `{bot_logic.signals_sent}`\n\n"
           f"🤖 *Le terminal reste en veille active.*")
    bot_tg.send_message(CHAT_ID, msg, parse_mode="Markdown")
    bot_logic.ticks_count = 0 # Reset pour prochaines 3h

def session_start():
    bot_logic.session_active = True
    bot_logic.sync_news()
    quote = random.choice(MOTIVATIONS_OPEN)
    bot_tg.send_message(CHAT_ID, f"🌅 **OUVERTURE SESSION (06:00 UTC)**\n\n💡 *{quote}*")

def session_end():
    bot_logic.session_active = False
    quote = random.choice(MOTIVATIONS_CLOSE)
    bot_tg.send_message(CHAT_ID, f"🌙 **CLÔTURE SESSION (21:00 UTC)**\n\n💤 *{quote}*")

# --- CORE LOGIC (WEBSOCKET) ---

def on_message(ws, message):
    data = json.loads(message)
    if 'tick' in data:
        bot_logic.ticks_count += 1
        # Logique de détection interne (SMC Engine)
        # 1. Detect Sweep -> send_pre_signal()
        # 2. Confirm BOS + Rejet -> send_final_signal()
        pass

def scheduler_loop():
    schedule.every(2).minutes.do(news_30min_checker)
    for h in ["09:00", "12:00", "15:00", "18:00"]:
        schedule.every().day.at(h).do(report_3h)
    schedule.every().day.at("06:00").do(session_start)
    schedule.every().day.at("21:00").do(session_end)
    while True:
        schedule.run_pending()
        time.sleep(30)

@app.route('/')
def health(): return "ONLINE", 200

if __name__ == "__main__":
    bot_tg.send_message(CHAT_ID, "🚀 **TERMINAL SNIPER SMC DÉPLOYÉ**\n*(Message unique de mise en ligne)*")
    bot_logic.session_active = True
    Thread(target=scheduler_loop).start()
    
    def run_ws():
        ws = websocket.WebSocketApp(f"wss://ws.binaryws.com/websockets/v3?app_id={APP_ID}",
                                    on_message=on_message,
                                    on_open=lambda ws: [ws.send(json.dumps({"authorize": API_TOKEN})),
                                                       [ws.send(json.dumps({"subscribe": a})) for a in ["XAUUSD", "BOOM500", "CRASH500", "R_100"]]])
        ws.run_forever()
    Thread(target=run_ws).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
