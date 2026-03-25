import streamlit as st
import json, requests, threading, time, os, websocket
from datetime import datetime
import pytz

# --- CONFIGURATION ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

st.set_page_config(page_title="Mc ANTHONIO VVIP v12.4", layout="wide")

class VVIPEngine:
    def __init__(self):
        self.scanned = 0
        self.signals = []
        self.is_running = False
        self.last_report_hour = -1

@st.cache_resource
def get_engine(): return VVIPEngine()
engine = get_engine()

def send_tg(msg):
    if TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=8)
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
            if rec_l < ext_l and curr_p > max(h[-12:-2]):
                tp1 = curr_p + (abs(ext_h - curr_p) * 0.5)
                setup = f"🟢 **BUY SNIPER** {symbol}\n📍 Entrée : `{curr_p}`\n🛡️ **SL :** `{round(rec_l, 2)}` \n🏆 **TP1 :** `{round(tp1, 2)}` | **TP2 :** `{round(ext_h, 2)}`"
            if rec_h > ext_h and curr_p < min(l[-12:-2]):
                tp1 = curr_p - (abs(curr_p - ext_l) * 0.5)
                setup = f"🔴 **SELL SNIPER** {symbol}\n📍 Entrée : `{curr_p}`\n🛡️ **SL :** `{round(rec_h, 2)}` \n🏆 **TP1 :** `{round(tp1, 2)}` | **TP2 :** `{round(ext_l, 2)}`"
            if setup:
                sig_id = f"{symbol}_{round(curr_p, 2)}"
                if sig_id not in [s.get('id', '') for s in engine.signals]:
                    engine.signals.append({"id": sig_id, "text": setup})
                    send_tg(f"🏛️ **Mc ANTHONIO VVIP**\n\n{setup}\n👤 @McAnthonio")
            engine.scanned += 1
    except: pass

def core_loop():
    while True:
        try:
            now = datetime.now(MAD_TZ)
            hr = now.hour
            # --- RAPPORTS AUTOMATIQUES TOUTES LES 3H ---
            if hr in [9, 12, 15, 18, 21] and engine.last_report_hour != hr:
                rapport = f"📊 **RAPPORT VVIP ({hr}h)**\n✅ Scans effectués : {engine.scanned}\n📈 Signaux trouvés : {len(engine.signals)}"
                send_tg(rapport)
                engine.last_report_hour = hr
            if 6 <= hr < 21:
                for m in MARKETS:
                    fetch_and_analyze(m)
                    time.sleep(6)
            else: time.sleep(60)
        except: time.sleep(10)

if not engine.is_running:
    threading.Thread(target=core_loop, daemon=True).start()
    engine.is_running = True

# --- INTERFACE ---
st.title("🏛️ Mc ANTHONIO VVIP - v12.4 Pro")
if st.button("🔄 ACTUALISER LA PAGE"): st.rerun()
c1, c2, c3 = st.columns(3)
c1.metric("Statut", "6h-21h", delta="LIVE")
c2.metric("Marchés", f"{len(MARKETS)} actifs")
c3.metric("Scans Totaux", engine.scanned)
for s in reversed(engine.signals[-10:]): st.success(s['text'])
time.sleep(30)
st.rerun()
