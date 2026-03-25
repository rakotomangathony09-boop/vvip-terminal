import streamlit as st
import json, requests, threading, time, os, websocket
from datetime import datetime
import pytz

# --- CONFIGURATION SYSTÈME ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

st.set_page_config(page_title="Mc ANTHONIO VVIP Elite", layout="wide", page_icon="🏛️")

# --- MÉMOIRE PERSISTANTE ---
class VVIPEngine:
    def __init__(self):
        self.scanned = 0
        self.signals = []
        self.logs = []
        self.is_running = False

    def add_log(self, msg):
        now = datetime.now(MAD_TZ).strftime('%H:%M:%S')
        self.logs = [f"[{now}] {msg}"] + self.logs[:10]

@st.cache_resource
def get_engine(): return VVIPEngine()
engine = get_engine()

def send_tg(msg):
    if TOKEN and CHAT_ID:
        try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                           json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
        except: pass

# --- ANALYSE SMC SNIPER 35% ---
def fetch_and_analyze(symbol):
    try:
        # Connexion courte (One-Shot) pour éviter le blocage Render
        ws = websocket.create_connection("wss://ws.binaryws.com/websockets/v3?app_id=1089", timeout=10)
        req = {"ticks_history": symbol, "count": 70, "end": "latest", "style": "candles", "granularity": 300}
        ws.send(json.dumps(req))
        result = json.loads(ws.recv())
        ws.close()

        if 'candles' in result:
            candles = result['candles']
            highs = [float(c['high']) for c in candles]
            lows = [float(c['low']) for c in candles]
            prices = [float(c['close']) for c in candles]
            curr_p = prices[-1]

            # Calcul des zones External et Internal
            ext_h, ext_l = max(highs[:-15]), min(lows[:-15])
            s_h, s_l = max(highs[-12:-3]), min(lows[-12:-3])

            setup = None
            # Logique BUY : Sweep + BOS + Pullback 35%
            if s_l < ext_l and max(highs[-3:-1]) > s_h and curr_p <= s_l + ((s_h - s_l) * 0.35):
                sl = s_l - ((s_h - s_l) * 0.15)
                tp1 = curr_p + ((ext_h - curr_p) * 0.50)
                tp2 = ext_h
                setup = f"🟢 **BUY {symbol}**\n📍 Entrée : `{curr_p}`\n🛡️ SL : `{round(sl, 2)}` | 🎯 TP1 : `{round(tp1, 2)}` | 🏆 TP2 : `{round(tp2, 2)}`"
            
            # Logique SELL : Sweep + BOS + Pullback 35%
            elif s_h > ext_h and min(lows[-3:-1]) < s_l and curr_p >= s_h - ((s_h - s_l) * 0.35):
                sl = s_h + ((s_h - s_l) * 0.15)
                tp1 = curr_p - ((curr_p - ext_l) * 0.50)
                tp2 = ext_l
                setup = f"🔴 **SELL {symbol}**\n📍 Entrée : `{curr_p}`\n🛡️ SL : `{round(sl, 2)}` | 🎯 TP1 : `{round(tp1, 2)}` | 🏆 TP2 : `{round(tp2, 2)}`"

            if setup:
                sig_id = f"{symbol}_{curr_p}"
                if sig_id not in [s.get('id', '') for s in engine.signals]:
                    t_now = datetime.now(MAD_TZ).strftime('%H:%M')
                    engine.signals.append({"id": sig_id, "text": setup, "time": t_now})
                    send_tg(f"🏛️ **Mc ANTHONIO VVIP SIGNAL**\n\n{setup}\n🛡️ Admin : Mc ANTHONIO")

            engine.scanned += 1
            if engine.scanned % 10 == 0:
                engine.add_log(f"✅ Scan actif : {symbol}")
    except:
        engine.add_log(f"❌ Erreur réseau sur {symbol}")

def background_loop():
    while True:
        for m in MARKETS:
            fetch_and_analyze(m)
            time.sleep(2)
        time.sleep(20)

if not engine.is_running:
    threading.Thread(target=background_loop, daemon=True).start()
    engine.is_running = True
    send_tg("🏛️ **Mc ANTHONIO VVIP : TERMINAL v11.0 DÉPLOYÉ**")

# --- INTERFACE ---
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v11.0")

col1, col2, col3 = st.columns(3)
col1.metric("Moteur", "OPÉRATIONNEL")
col2.metric("Signaux", len(engine.signals))
col3.metric("Scans Actifs", engine.scanned)

st.divider()
c_left, c_right = st.columns([2, 1])

with c_left:
    st.subheader("📊 Signaux Sniper 35%")
    if not engine.signals:
        st.info("Le scanner est en route. Attente d'un setup institutionnel...")
    for s in reversed(engine.signals):
        st.success(f"🕙 {s['time']} | {s['text']}")

with c_right:
    st.subheader("📜 Diagnostic")
    for l in engine.logs: st.code(l)
    if st.button("🔄 Rafraîchir"): st.rerun()

time.sleep(30)
st.rerun()
