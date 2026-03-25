import streamlit as st
import json, requests, websocket, threading, time, os
from datetime import datetime
import pytz

# --- CONFIGURATION ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

st.set_page_config(page_title="Mc ANTHONIO VVIP", layout="wide")

# --- ENGINE PERSISTANT ---
class TradingEngine:
    def __init__(self):
        self.scanned = 0
        self.signals_count = 0
        self.signals = []
        self.logs = []
        self.is_running = False

    def log(self, msg):
        now = datetime.now(MAD_TZ).strftime('%H:%M:%S')
        self.logs = [f"[{now}] {msg}"] + self.logs[:15]

@st.cache_resource
def get_engine():
    return TradingEngine()

engine = get_engine()

def send_tg(msg):
    if TOKEN and CHAT_ID:
        try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                           json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        except: pass

# --- LOGIQUE SMC ---
def run_smc(candles, symbol):
    engine.scanned += 1
    if len(candles) < 70: return
    
    h = [float(x['high']) for x in candles]
    l = [float(x['low']) for x in candles]
    c = [float(x['close']) for x in candles]
    curr = c[-1]
    
    ext_h, ext_l = max(h[-70:-15]), min(l[-70:-15])
    s_h, s_l = max(h[-12:-3]), min(l[-12:-3])

    setup = None
    if s_l < ext_l and max(h[-3:-1]) > s_h and curr <= s_l + ((s_h - s_l) * 0.35):
        setup = f"🟢 **BUY {symbol}**\n📍 Entry : `{curr}`"
    elif s_h > ext_h and min(l[-3:-1]) < s_l and curr >= s_h - ((s_h - s_l) * 0.35):
        setup = f"🔴 **SELL {symbol}**\n📍 Entry : `{curr}`"

    if setup:
        engine.signals.append({"text": setup, "time": datetime.now(MAD_TZ).strftime('%H:%M')})
        engine.signals_count += 1
        send_tg(f"🏛️ **Mc ANTHONIO VVIP**\n\n{setup}")

# --- WEBSOCKET ---
def start_ws():
    engine.log("Tentative de connexion aux marchés...")
    while True:
        try:
            ws = websocket.WebSocketApp("wss://ws.binaryws.com/websockets/v3?app_id=1089",
                on_open=lambda ws: [ws.send(json.dumps({"ticks_history": s, "subscribe": 1, "count": 100, "granularity": 300, "style": "candles"})) for s in MARKETS],
                on_message=lambda ws, m: run_smc(json.loads(m)['candles'], json.loads(m)['echo_req']['ticks_history']) if 'candles' in json.loads(m) else None,
                on_error=lambda ws, e: engine.log(f"Erreur: {e}"))
            ws.run_forever()
        except: 
            engine.log("Reconnexion...")
            time.sleep(10)

# --- LANCEMENT ---
if not engine.is_running:
    threading.Thread(target=start_ws, daemon=True).start()
    engine.is_running = True
    send_tg("🏛️ **Mc ANTHONIO VVIP : SYSTÈME DÉMARRÉ**")

# --- UI ---
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v10.8")

c1, c2, c3 = st.columns(3)
c1.metric("Moteur", "OPÉRATIONNEL" if engine.is_running else "ARRÊTÉ")
c2.metric("Signaux", engine.signals_count)
c3.metric("Scans Actifs", engine.scanned)

st.divider()

col_main, col_side = st.columns([2, 1])

with col_main:
    st.subheader("📊 Derniers Signaux")
    if not engine.signals:
        st.info("En attente de patterns Sniper 35%...")
    for s in reversed(engine.signals):
        st.success(f"{s['time']} | {s['text']}")

with col_side:
    st.subheader("📜 Logs Interne")
    for l in engine.logs:
        st.write(l)
    if st.button("Actualiser"): st.rerun()

time.sleep(15)
st.rerun()
