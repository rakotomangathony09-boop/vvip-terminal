import streamlit as st
import json, requests, websocket, threading, time, os
from datetime import datetime
import pytz

# --- CONFIGURATION SYSTÈME ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Les 12 actifs surveillés
MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]
APP_URL = "https://vvip-terminal-9-9.onrender.com"

st.set_page_config(page_title="Mc ANTHONIO VVIP", layout="wide", page_icon="🏛️")

# --- MOTEUR PERSISTANT (Empêche le reset à 0) ---
class VVIPEngine:
    def __init__(self):
        self.scanned = 0
        self.signals = []
        self.signals_count = 0
        self.logs = []
        self.is_running = False
        self.last_6h = ""
        self.last_21h = ""

    def add_log(self, msg):
        now = datetime.now(MAD_TZ).strftime('%H:%M:%S')
        self.logs = [f"[{now}] {msg}"] + self.logs[:14]

@st.cache_resource
def get_engine():
    return VVIPEngine()

engine = get_engine()

# --- FONCTIONS DE COMMUNICATION ---
def send_telegram(msg):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

# --- LOGIQUE SMC SNIPER 35% ---
def run_smc_logic(candles, symbol):
    engine.scanned += 1
    if len(candles) < 70: return
    
    h = [float(x['high']) for x in candles]
    l = [float(x['low']) for x in candles]
    c = [float(x['close']) for x in candles]
    curr_p = c[-1]
    
    ext_h, ext_l = max(h[-70:-15]), min(l[-70:-15])
    s_h, s_l = max(h[-12:-3]), min(l[-12:-3])

    setup = None
    # BUY 35%
    if s_l < ext_l and max(h[-3:-1]) > s_h and curr_p <= s_l + ((s_h - s_l) * 0.35):
        tp2, tp1 = ext_h, curr_p + ((ext_h - curr_p) * 0.50)
        setup = f"🟢 **BUY {symbol}**\n📍 Entrée : `{curr_p}`\n🎯 TP1 : `{round(tp1, 2)}` | TP2 : `{round(tp2, 2)}`"
    
    # SELL 35%
    elif s_h > ext_h and min(l[-3:-1]) < s_l and curr_p >= s_h - ((s_h - s_l) * 0.35):
        tp2, tp1 = ext_l, curr_p - ((curr_p - ext_l) * 0.50)
        setup = f"🔴 **SELL {symbol}**\n📍 Entrée : `{curr_p}`\n🎯 TP1 : `{round(tp1, 2)}` | TP2 : `{round(tp2, 2)}`"

    if setup:
        sig_id = f"{symbol}_{setup[:15]}"
        if sig_id not in [s.get('id') for s in engine.signals[-5:]]:
            t_now = datetime.now(MAD_TZ).strftime('%H:%M')
            engine.signals.append({"id": sig_id, "text": setup, "time": t_now})
            engine.signals_count += 1
            send_telegram(f"🏛️ **Mc ANTHONIO VVIP SIGNAL**\n\n{setup}\n🛡️ Admin : Mc ANTHONIO")

# --- SERVICES D'ARRIÈRE-PLAN ---
def start_ws():
    engine.add_log("🚀 Initialisation du WebSocket...")
    while True:
        try:
            ws = websocket.WebSocketApp("wss://ws.binaryws.com/websockets/v3?app_id=1089",
                on_open=lambda ws: [ws.send(json.dumps({"ticks_history": s, "subscribe": 1, "count": 100, "granularity": 300, "style": "candles"})) for s in MARKETS],
                on_message=lambda ws, m: run_smc_logic(json.loads(m)['candles'], json.loads(m)['echo_req']['ticks_history']) if 'candles' in json.loads(m) else None,
                on_error=lambda ws, e: engine.add_log(f"⚠️ Erreur: {e}"))
            ws.run_forever()
        except: 
            time.sleep(10)

def daily_scheduler():
    while True:
        now = datetime.now(MAD_TZ)
        cur_t, cur_d = now.strftime("%H:%M"), now.strftime("%Y-%m-%d")
        
        if "06:00" <= cur_t <= "06:05" and engine.last_6h != cur_d:
            send_telegram("🌅 **MOTIVATION VVIP**\n\nFocus et discipline. Le terminal est prêt.\n🛡️ **Mc ANTHONIO**")
            engine.signals_count = 0
            engine.last_6h = cur_d
        
        if "21:00" <= cur_t <= "21:05" and engine.last_21h != cur_d:
            msg = f"✅ {engine.signals_count} signaux." if engine.signals_count > 0 else "🛡️ Marché protégé."
            send_telegram(f"🌃 **RAPPORT DU SOIR**\n\n📊 **Activité :**\n- Scans : {engine.scanned}\n- Résultat : {msg}")
            engine.last_21h = cur_d
        time.sleep(60)

def keep_alive():
    while True:
        try: requests.get(APP_URL, timeout=10)
        except: pass
        time.sleep(600)

# --- LANCEMENT DES THREADS (Une seule fois) ---
if not engine.is_running:
    threading.Thread(target=start_ws, daemon=True).start()
    threading.Thread(target=daily_scheduler, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    engine.is_running = True
    send_telegram("🏛️ **Mc ANTHONIO VVIP : SYSTÈME ACTIF (70/35%)**")

# --- INTERFACE GRAPHIQUE ---
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v10.8 Elite")

col1, col2, col3 = st.columns(3)
col1.metric("Moteur Status", "OPÉRATIONNEL" if engine.is_running else "ERREUR")
col2.metric("Signaux Validés", engine.signals_count)
col3.metric("Scans Actifs", engine.scanned)

st.divider()

c_left, c_right = st.columns([2, 1])

with c_left:
    st.subheader("📊 Derniers Signaux Sniper 35%")
    if not engine.signals:
        st.info("Scan en cours sur 12 marchés... Attente d'un setup institutionnel.")
    else:
        for s in reversed(engine.signals):
            with st.expander(f"{s['text'].splitlines()[0]} - {s['time']}", expanded=True):
                st.markdown(s['text'])

with c_right:
    st.subheader("📜 Console de Diagnostic")
    for log in engine.logs:
        st.code(log)
    if st.button("🔄 Rafraîchir l'écran"):
        st.rerun()

# Auto-refresh toutes les 20 secondes
time.sleep(20)
st.rerun()
