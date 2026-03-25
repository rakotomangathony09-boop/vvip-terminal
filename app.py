import streamlit as st
import json, requests, threading, time, os, websocket
from datetime import datetime
import pytz

# --- 1. CONFIGURATION ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

st.set_page_config(page_title="Mc ANTHONIO VVIP v12.1", layout="wide", page_icon="🏛️")

class VVIPEngine:
    def __init__(self):
        self.scanned = 0
        self.signals = []
        self.is_running = False
        self.logs = []
        self.last_report_hour = -1

    def add_log(self, msg):
        now = datetime.now(MAD_TZ).strftime('%H:%M')
        self.logs = [f"[{now}] {msg}"] + self.logs[:5]

@st.cache_resource
def get_engine(): return VVIPEngine()
engine = get_engine()

def send_tg(msg):
    if TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
        except: pass

# --- 2. ANALYSE TECHNIQUE (SMC + SL + TP1/TP2) ---
def fetch_and_analyze(symbol):
    try:
        ws = websocket.create_connection("wss://ws.binaryws.com/websockets/v3?app_id=1089", timeout=12)
        ws.send(json.dumps({"ticks_history": symbol, "count": 100, "style": "candles", "granularity": 300}))
        res = json.loads(ws.recv()); ws.close()

        if 'candles' in res:
            c = res['candles']
            h, l, cl = [float(x['high']) for x in c], [float(x['low']) for x in c], [float(x['close']) for x in c]
            curr_p, ext_h, ext_l = cl[-1], max(h[20:80]), min(l[20:80])

            setup = None
            # Logique BUY
            rec_l = min(l[-15:])
            if rec_l < ext_l and curr_p > max(h[-12:-2]):
                if curr_p <= ext_l + (abs(ext_l - rec_l) * 0.40):
                    tp2 = ext_h
                    tp1 = curr_p + (abs(tp2 - curr_p) * 0.5)
                    setup = f"🟢 **BUY SNIPER** {symbol}\n📍 Entrée : `{curr_p}`\n🛡️ **SL :** `{round(rec_l, 2)}` \n🏆 **TP1 :** `{round(tp1, 2)}` | **TP2 :** `{round(tp2, 2)}`"

            # Logique SELL
            rec_h = max(h[-15:])
            if rec_h > ext_h and curr_p < min(l[-12:-2]):
                if curr_p >= ext_h - (abs(rec_h - ext_h) * 0.40):
                    tp2 = ext_l
                    tp1 = curr_p - (abs(curr_p - tp2) * 0.5)
                    setup = f"🔴 **SELL SNIPER** {symbol}\n📍 Entrée : `{curr_p}`\n🛡️ **SL :** `{round(rec_h, 2)}` \n🏆 **TP1 :** `{round(tp1, 2)}` | **TP2 :** `{round(tp2, 2)}`"

            if setup:
                sig_id = f"{symbol}_{round(curr_p, 2)}"
                if sig_id not in [s.get('id', '') for s in engine.signals]:
                    engine.signals.append({"id": sig_id, "text": setup})
                    send_tg(f"🏛️ **Mc ANTHONIO VVIP**\n\n{setup}\n👤 @McAnthonio")
            engine.scanned += 1
    except: pass

# --- 3. BOUCLE DE CONTRÔLE (HORAIRES & RAPPORTS) ---
def core_loop():
    engine.add_log("Système Initialisé")
    while True:
        try:
            now = datetime.now(MAD_TZ)
            hr = now.hour

            # Rapports automatiques chaque 3h (9h, 12h, 15h, 18h, 21h)
            if hr in [9, 12, 15, 18, 21] and engine.last_report_hour != hr:
                send_tg(f"📊 **RAPPORT VVIP ({hr}h)**\n✅ Scans : {engine.scanned}\n📈 Signaux : {len(engine.signals)}")
                engine.last_report_hour = hr

            # Plage de scan : 06h à 21h
            if 6 <= hr < 21:
                for m in MARKETS:
                    fetch_and_analyze(m)
                    time.sleep(5)
            else:
                engine.add_log("Mode Veille (Repos)")
                time.sleep(60)
        except:
            time.sleep(10)

if not engine.is_running:
    threading.Thread(target=core_loop, daemon=True).start()
    engine.is_running = True

# --- 4. INTERFACE ---
st.title("🏛️ Mc ANTHONIO VVIP - v12.1 Elite")

col1, col2, col3 = st.columns(3)
col1.metric("Statut", "6h - 21h", delta="ACTIF")
col2.metric("Marchés", f"{len(MARKETS)} actifs")
col3.metric("Scans Totaux", engine.scanned)

st.divider()

l, r = st.columns([2, 1])
with l:
    st.subheader("📊 Signaux Sniper (SL & Double TP)")
    if not engine.signals:
        st.info("Recherche de zones de liquidité...")
    for s in reversed(engine.signals[-10:]):
        st.success(s['text'])

with r:
    st.subheader("📜 Diagnostic")
    st.write(f"Dernier scan à : {datetime.now(MAD_TZ).strftime('%H:%M:%S')}")
    for log in engine.logs:
        st.code(log)
    if st.button("🔄 Actualiser"):
        st.rerun()

time.sleep(30)
st.rerun()
