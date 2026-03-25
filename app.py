import json, requests, threading, time, os, websocket
from datetime import datetime
import pytz

# --- CONFIGURATION ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MARKETS = ["R_10", "R_25", "R_50", "R_75", "R_100",
           "B_300", "B_500", "B_1000",
           "C_300", "C_500", "C_1000"]

class VVIPBot:
    def __init__(self):
        self.scanned = 0
        self.sent_signals = []
        self.last_report_hour = -1
        self.day_started = False
        self.day_ended = False

bot = VVIPBot()

# --- TELEGRAM ---
def send_tg(msg):
    if TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown"
            }, timeout=10)
        except:
            pass

# --- ANALYSE PRINCIPALE ---
def fetch_and_analyze(symbol):
    try:
        ws = websocket.create_connection(
            "wss://ws.binaryws.com/websockets/v3?app_id=1089",
            timeout=15
        )

        ws.send(json.dumps({
            "ticks_history": symbol,
            "count": 100,
            "style": "candles",
            "granularity": 300
        }))

        res = json.loads(ws.recv())
        ws.close()

        if 'candles' not in res:
            return

        c = res['candles']

        h = [float(x['high']) for x in c]
        l = [float(x['low']) for x in c]
        cl = [float(x['close']) for x in c]

        curr_p = cl[-1]

        # ===============================
        # 🔥 STRATÉGIE SMC (TON IMAGE)
        # ===============================

        # 1. Zones de liquidité
        major_h = max(h[20:85])
        major_l = min(l[20:85])

        # 2. Détection sweep (bougie précédente)
        sweep_sell = h[-2] > major_h and cl[-2] < major_h
        sweep_buy = l[-2] < major_l and cl[-2] > major_l

        # 3. Structure marché (BOS)
        last_low = min(l[-10:-2])
        last_high = max(h[-10:-2])

        # 4. Filtre tendance simple
        trend_up = cl[-1] > cl[-20]
        trend_down = cl[-1] < cl[-20]

        setup = None

        # 🔴 SELL confirmé (Sweep + BOS)
        if sweep_sell and cl[-1] < last_low and trend_down:

            entry = curr_p
            sl = h[-2]
            tp_final = major_l

            rr = abs(entry - tp_final)
            tp1 = entry - rr * 0.5

            setup = (f"🔴 **SMC SELL CONFIRMÉ** {symbol}\n"
                     f"⚠️ Sweep + BOS validé\n\n"
                     f"📍 Entry : `{entry}`\n"
                     f"🛡️ SL : `{round(sl,2)}`\n"
                     f"🎯 TP1 : `{round(tp1,2)}`\n"
                     f"💎 TP Final : `{round(tp_final,2)}`")

        # 🟢 BUY confirmé (inverse)
        elif sweep_buy and cl[-1] > last_high and trend_up:

            entry = curr_p
            sl = l[-2]
            tp_final = major_h

            rr = abs(tp_final - entry)
            tp1 = entry + rr * 0.5

            setup = (f"🟢 **SMC BUY CONFIRMÉ** {symbol}\n"
                     f"⚠️ Sweep + BOS validé\n\n"
                     f"📍 Entry : `{entry}`\n"
                     f"🛡️ SL : `{round(sl,2)}`\n"
                     f"🎯 TP1 : `{round(tp1,2)}`\n"
                     f"💎 TP Final : `{round(tp_final,2)}`")

        # --- ENVOI SIGNAL ---
        if setup:
            sig_id = f"{symbol}_{round(curr_p, 1)}"

            if sig_id not in bot.sent_signals:
                bot.sent_signals.append(sig_id)

                send_tg(
                    f"🏛️ **STRATÉGIE INSTITUTIONNELLE SMC**\n\n"
                    f"{setup}\n\n"
                    f"👤 @McAnthonio"
                )

                if len(bot.sent_signals) > 40:
                    bot.sent_signals.pop(0)

        bot.scanned += 1

    except Exception as e:
        print(f"Erreur sur {symbol}: {e}")

# --- BOUCLE PRINCIPALE ---
def run_bot():
    print("🚀 Bot SMC lancé...")

    while True:
        threads = []

        for symbol in MARKETS:
            t = threading.Thread(target=fetch_and_analyze, args=(symbol,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        time.sleep(10)  # scan toutes les 10 secondes

# --- START ---
if __name__ == "__main__":
    run_bot()
