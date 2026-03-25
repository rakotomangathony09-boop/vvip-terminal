import json, requests, threading, time, os, websocket, random
from datetime import datetime
import pytz

# --- CONFIGURATION ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

MOTIVATIONS = [
    "Le succès n'est pas final, l'échec n'est pas fatal : c'est le courage de continuer qui compte.",
    "Le trading ne consiste pas à prédire l'avenir, mais à avoir un système qui gère les probabilités.",
    "Le marché est un miroir. Il ne vous donne pas ce que vous voulez, il vous donne ce que vous méritez par votre discipline.",
    "N'ayez pas peur de rater un trade, ayez peur de ne pas respecter votre plan.",
    "Le but d'un trader n'est pas de faire de l'argent, mais de faire de bons trades."
]

DISCIPLINE_RULES = [
    "Règle n°1 : Ne jamais trader sans Stop Loss.",
    "Règle n°2 : La patience paie plus que l'agressivité.",
    "Règle n°3 : Acceptez la perte comme un coût d'exploitation.",
    "Règle n°4 : Si le setup SMC n'est pas parfait, on reste spectateur.",
    "Règle n°5 : Votre capital est votre outil de travail. Protégez-le."
]

class VVIPBot:
    def __init__(self):
        self.scanned = 0
        self.signals = []
        self.last_report_hour = -1
        self.day_started = False
        self.day_ended = False

bot = VVIPBot()

def send_tg(msg):
    if TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        except: pass

def fetch_and_analyze(symbol):
    try:
        ws = websocket.create_connection("wss://ws.binaryws.com/websockets/v3?app_id=1089", timeout=15)
        ws.send(json.dumps({"ticks_history": symbol, "count": 100, "style": "candles", "granularity": 300}))
        res = json.loads(ws.recv())
        ws.close()
        
        if 'candles' in res:
            c = res['candles']
            h, l, cl = [float(x['high']) for x in c], [float(x['low']) for x in c], [float(x['close']) for x in c]
            curr_p, ext_h, ext_l = cl[-1], max(h[20:80]), min(l[20:80])
            
            setup = None
            rec_l, rec_h = min(l[-15:]), max(h[-15:])

            if rec_l < ext_l and curr_p > max(h[-12:-2]): # BUY
                tp2 = ext_h
                tp1 = curr_p + (abs(tp2 - curr_p) * 0.5)
                setup = f"🟢 **BUY SNIPER** {symbol}\n📍 Entrée : `{curr_p}`\n🛡️ **SL :** `{round(rec_l, 2)}` \n🏆 **TP1 :** `{round(tp1, 2)}` | **TP2 :** `{round(tp2, 2)}`"

            elif rec_h > ext_h and curr_p < min(l[-12:-2]): # SELL
                tp2 = ext_l
                tp1 = curr_p - (abs(curr_p - tp2) * 0.5)
                setup = f"🔴 **SELL SNIPER** {symbol}\n📍 Entrée : `{curr_p}`\n🛡️ **SL :** `{round(rec_h, 2)}` \n🏆 **TP1 :** `{round(tp1, 2)}` | **TP2 :** `{round(tp2, 2)}`"

            if setup:
                sig_id = f"{symbol}_{round(curr_p, 2)}"
                if sig_id not in bot.signals:
                    bot.signals.append(sig_id)
                    send_tg(f"🏛️ **VVIP Signal by Mc Anthonio**\n\n{setup}\n👤 @McAnthonio")
            bot.scanned += 1
    except: pass

def run_bot():
    send_tg("🚀 **VVIP v13.0 Elite Mindset Online.**\nLe scanner et le coach de discipline sont prêts.")
    
    while True:
        try:
            now = datetime.now(MAD_TZ)
            hr = now.hour

            if hr == 6 and not bot.day_started:
                msg = f"☀️ **SESSION OUVERTE**\n\n💡 *Motivation :*\n\"{random.choice(MOTIVATIONS)}\"\n\n🛡️ *Discipline :*\n{random.choice(DISCIPLINE_RULES)}\n\n🚀 Scan en cours..."
                send_tg(msg)
                bot.day_started = True
                bot.day_ended = False

            if hr in [9, 12, 15, 18] and bot.last_report_hour != hr:
                rapport = f"📊 **RAPPORT ({hr}h)**\n✅ Scans : {bot.scanned}\n📈 Signaux : {len(bot.signals)}"
                send_tg(rapport)
                bot.last_report_hour = hr

            if hr == 21 and not bot.day_ended:
                msg = f"🌑 **SESSION TERMINÉE**\n\n🏆 *Bilan :*\n🔄 Scans : {bot.scanned}\n📈 Signaux : {len(bot.signals)}\n\nÀ demain 06h00 !"
                send_tg(msg)
                bot.day_ended = True
                bot.day_started = False
                bot.scanned = 0
                bot.signals = []

            if 6 <= hr < 21:
                for m in MARKETS:
                    fetch_and_analyze(m)
                    time.sleep(15) 
            else:
                time.sleep(60)
        except Exception:
            time.sleep(30)

if __name__ == "__main__":
    run_bot()
