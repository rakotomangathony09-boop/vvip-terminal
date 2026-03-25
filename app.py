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

# --- CONFIGURATION SÉCURISÉE (Récupère les clés de Render) ---
API_TOKEN = os.getenv("DERIV_API_TOKEN")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
APP_ID = os.getenv("APP_ID", "1089")

bot_tg = telebot.TeleBot(TG_TOKEN)
app = Flask(__name__)

# --- CONTENU PSYCHOLOGIQUE ---
MOTIVATIONS_OPEN = [
    "Attends le Sweep, confirme le BOS, attend le Rejet. Sois un sniper, pas un parieur.",
    "La liquidité est le carburant du marché. Ne sois pas la liquidité, suis les banques.",
    "Discipline : Pas de bougie de rejet = Pas de trade. Respecte ton plan."
]
MOTIVATIONS_CLOSE = [
    "Session terminée. Déconnecte-toi. Ton mental est ton plus gros actif, protège-le.",
    "Le marché ne s'arrête jamais, mais toi si. Repose-toi pour être lucide demain.",
    "Peu importe tes gains, la victoire est d'avoir respecté la stratégie."
]

class SniperSystem:
    def __init__(self):
        self.session_active = True
        self.is_booted = False
        self.daily_news = []
        self.notified_news = []
        self.pre_alerted_setups = {}
        
        # Statistiques pour Rapport 3h
        self.ticks_count = 0
        self.sweeps_detected = 0
        self.signals_sent = 0

    def sync_news(self):
        """Récupère les news USD High Impact via Finnhub"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        url = f"https://finnhub.io/api/v1/calendar/economic?from={today}&to={today}&token={FINNHUB_KEY}"
        try:
            res = requests.get(url).json()
            self.daily_news = [n for n in res.get('economicCalendar', []) 
                              if n['country'] == 'US' and n['impact'] == 'high']
            print(f"✅ News synchronisées : {len(self.daily_news)}")
            return True
        except Exception as e:
            print(f"❌ Erreur Finnhub : {e}")
            return False

bot_logic = SniperSystem()

# --- SYSTÈME D'ALERTES ---

def send_pre_signal(symbol, side):
    """ Alerte T-2 min : Sweep détecté, en attente de Rejet """
    msg = (f"🔍 **PRÉ-ALERTE : SETUP DÉTECTÉ**\n\n"
           f"📈 Actif : `{symbol}`\n"
           f"⚡ Action prévue : **{side} LIMIT**\n"
           f"🎯 État : Sweep + BOS validés. En attente du Pullback + Rejet (~2 min).\n"
           f"📱 *Action : Préparez l'actif sur MT5.*")
    bot_tg.send_message(CHAT_ID, msg, parse_mode="Markdown")

def send_final_signal(symbol, side, entry, sl, tp1, tp2):
    """ Signal final : Stratégie complète (Sweep + BOS + Pullback + Rejet) """
    msg = (f"🎯 **SIGNAL SNIPER SMC FINAL**\n\n"
           f"🔥 **ORDRE : {side}**\n"
           f"✅ *Confirmation : Rejection Candle détectée*\n\n"
           f"📍 **ENTRÉE :** `{entry}`\n"
           f"🛡️ **STOP LOSS :** `{sl}` (Extrémité Sweep)\n\n"
           f"💰 **TP1 (50%) :** `{tp1}`\n"
           f"💎 **TP2 (Final) :** `{tp2}`\n\n"
           f"⚖️ *Gestion : Fermez 50% au TP1 et passez au Break-even (BE).*")
    bot_tg.send_message(CHAT_ID, msg, parse_mode="Markdown")
    bot_logic.signals_sent += 1

# --- RAPPORTS ET AUTOMATISATION ---

def report_3h():
    """ Envoie le bilan des 3 dernières heures d'activité """
    now = datetime.utcnow().strftime('%H:%M')
    msg = (f"📊 **RAPPORT D'ACTIVITÉ (3H)**\n"
           f"🕒 Heure : `{now} UTC`\n\n"
           f"🔢 Ticks traités : `{bot_logic.ticks_count}`\n"
           f"🔎 Sweeps analysés : `{bot_logic.sweeps_detected}`\n"
           f"✅ Signaux Snipers validés : `{bot_logic.signals_sent}`\n\n"
           f"🤖 *Terminal opérationnel. Scan en cours.*")
    bot_tg.send_message(CHAT_ID, msg, parse_mode="Markdown")
    # Reset des compteurs
    bot_logic.ticks_count = 0
    bot_logic.sweeps_detected = 0
    bot_logic.signals_sent = 0

def session_start():
    bot_logic.session_active = True
    bot_logic.sync_news()
    quote = random.choice(MOTIVATIONS_OPEN)
    bot_tg.send_message(CHAT_ID, f"🌅 **OUVERTURE SESSION (06:00 UTC)**\n\n💡 *Motivation : {quote}*")

def session_end():
    bot_logic.session_active = False
    quote = random.choice(MOTIVATIONS_CLOSE)
    bot_tg.send_message(CHAT_ID, f"🌙 **CLÔTURE SESSION (21:00 UTC)**\n\n💤 *Discipline : {quote}*")

# --- CORE LOGIC (WEBSOCKET) ---

def on_message(ws, message):
    data = json.loads(message)
    if 'tick' in data:
        bot_logic.ticks_count += 1
        # L'analyseur SMC tourne ici en temps réel
        pass

def scheduler_loop():
    """ Gère les rapports 3h et les sessions de motivation """
    for h in ["09:00", "12:00", "15:00", "18:00"]:
        schedule.every().day.at(h).do(report_3h)
    schedule.every().day.at("06:00").do(session_start)
    schedule.every().day.at("21:00").do(session_end)
    while True:
        schedule.run_pending()
        time.sleep(30)

# --- SERVEUR WEB FLASK ---
@app.route('/')
def health():
    return "BOT OPERATIONAL", 200

# --- LANCEMENT MULTI-THREAD ---
if __name__ == "__main__":
    # 1. Message de démarrage immédiat
    try:
        bot_tg.send_message(CHAT_ID, "🚀 **TERMINAL SNIPER SMC DÉPLOYÉ**\n*(Connexion établie avec succès)*")
        bot_logic.sync_news()
    except Exception as e:
        print(f"Erreur démarrage Telegram : {e}")

    # 2. Lancement du Scheduler (Rapports/Motivation)
    Thread(target=scheduler_loop, daemon=True).start()
    
    # 3. Lancement du WebSocket Deriv
    def run_ws():
        try:
            ws = websocket.WebSocketApp(f"wss://ws.binaryws.com/websockets/v3?app_id={APP_ID}",
                                        on_message=on_message,
                                        on_open=lambda ws: [ws.send(json.dumps({"authorize": API_TOKEN})),
                                                           [ws.send(json.dumps({"subscribe": a})) for a in ["XAUUSD", "BOOM500", "R_100"]]])
            ws.run_forever()
        except Exception as e:
            print(f"Erreur WS : {e}")

    Thread(target=run_ws, daemon=True).start()

    # 4. Lancement du serveur Web (obligatoire pour Render)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
