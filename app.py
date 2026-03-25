import streamlit as st
import json, requests, websocket, threading, time, os
from datetime import datetime
import pytz

# --- CONFIGURATION SYSTÈME ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')

# --- RÉCUPÉRATION SÉCURISÉE DES CLÉS (Via Render Environment Variables) ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]
APP_URL = "https://vvip-terminal-9-9.onrender.com"

st.set_page_config(page_title="Mc ANTHONIO VVIP", layout="wide", page_icon="🏛️")

# --- INITIALISATION DES ÉTATS ---
if "signals" not in st.session_state: st.session_state.signals = []
if "signals_count" not in st.session_state: st.session_state.signals_count = 0
if "scanned_candles" not in st.session_state: st.session_state.scanned_candles = 0
if "logs" not in st.session_state: st.session_state.logs = []

def add_log(msg):
    now = datetime.now(MAD_TZ).strftime('%H:%M:%S')
    entry = f"[{now}] {msg}"
    st.session_state.logs = [entry] + st.session_state.logs[:29]

def send_telegram(msg):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

# --- SERVICES D'ARRIÈRE-PLAN ---
def keep_alive():
    while True:
        try: requests.get(APP_URL, timeout=10)
        except: pass
        time.sleep(600)

def daily_scheduler():
    last_sent_date_6h = ""
    last_sent_date_21h = ""
    while True:
        now = datetime.now(MAD_TZ)
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")
        
        if "06:00" <= current_time <= "06:05" and last_sent_date_6h != current_date:
            send_telegram("🌅 **PRÉPARATION VVIP**\n\nTerminal actif. Focus sur le Sniper 35%.\n🛡️ **Admin : Mc ANTHONIO**")
            st.session_state.signals_count = 0
            last_sent_date_6h = current_date
        
        if "21:00" <= current_time <= "21:05" and last_sent_date_21h != current_date:
            res = f"✅ {st.session_state.signals_count} signaux." if st.session_state.signals_count > 0 else "🛡️ Marché protégé."
            send_telegram(f"🌃 **RAPPORT DU SOIR VVIP**\n\n📊 **Activité :**\n- Scans : {st.session_state.scanned_candles}\n- Résultat : {res}")
            last_sent_date_21h = current_date
        time.sleep(60)

# --- ANALYSE SMC SNIPER 35% (70 BOUGIES) ---
def run_smc_logic(candles, symbol):
    st.session_state.scanned_candles += 1
    if len(candles) < 70: return
    
    h = [float(x['high']) for x in candles]
    l = [float(x['low']) for x in candles]
    c = [float(x['close']) for x in candles]
    curr_p = c[-1]
    
    # Structure Long Terme (70 bougies) vs Structure Récente (12 bougies)
    ext_h, ext_l = max(h[-70:-15]), min(l[-70:-15])
    s_h, s_l = max(h[-12:-3]), min(l[-12:-3])

    setup = None
    # LOGIQUE BUY (Retrait 35%)
    if s_l < ext_l and max(h[-3:-1]) > s_h and curr_p <= s_l + ((s_h - s_l) * 0.35):
        tp2, tp1 = ext_h, curr_p + ((ext_h - curr_p) * 0.50)
        setup = f"🟢 **BUY {symbol}**\n📍 Entrée : `{curr_p}`\n🎯 TP1 : `{round(tp1, 2)}` | TP2 : `{round(tp2, 2)}`"
    
    # LOGIQUE SELL (Retrait 35%)
    elif s_h > ext_h and min(l[-3:-1]) < s_l and curr_p >= s_h - ((s_h - s_l) * 0.35):
        tp2, tp1 = ext_l, curr_p - ((curr_p - ext_l) * 0.50)
        setup = f"🔴 **SELL {symbol}**\n📍 Entrée : `{curr_p}`\n🎯 TP1 : `{round(tp1, 2)}` | TP2 : `{round(tp2, 2)}`"

    if setup:
        sig_id = f"{symbol}_{setup[:10]}"
        if sig_id not in [s.get('id') for s in st.session_state.signals[-5:]]:
            st.session_state.signals.append({"id": sig_id, "text": setup, "time": datetime.now(MAD_TZ).strftime('%H:%M')})
            st.session_state.signals_count += 1
            send_telegram(f"🏛️ **Mc ANTHONIO VVIP SIGNAL (35%)**\n\n{setup}\n🛡️ Admin : Mc ANTHONIO")

def start_socket():
    while True:
        try:
            ws = websocket.WebSocketApp("wss://ws.binaryws.com/websockets/v3?app_id=1089",
                on_open=lambda ws: [ws.send(json.dumps({"ticks_history": s, "subscribe": 1, "count": 100, "granularity": 300, "style": "candles"})) for s in MARKETS],
                on_message=lambda ws, m: run_smc_logic(json.loads(m)['candles'], json.loads(m)['echo_req']['ticks_history']) if 'candles' in json.loads(m) else None)
            ws.run_forever()
        except: time.sleep(10)

# --- BOOTSTRAP DU MOTEUR ---
@st.cache_resource
def start_vvip_engine():
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=start_socket, daemon=True).start()
    threading.Thread(target=daily_scheduler, daemon=True).start()
    send_telegram("🏛️ **Mc ANTHONIO VVIP : MOTEUR ULTRA-STABLE ACTIF (70/35%)**\n\n✅ Connexion sécurisée\n🛡️ Admin : Mc ANTHONIO")
    return True

engine_active = start_vvip_engine()

# --- INTERFACE ---
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v10.8 Elite")

c1, c2, c3 = st.columns(3)
c1.metric("Moteur", "OPÉRATIONNEL" if engine_active else "ERREUR")
c2.metric("Signaux du jour", st.session_state.signals_count)
c3.metric("Scans Actifs", st.session_state.scanned_candles)

st.divider()

st.subheader("📊 Derniers Signaux Sniper 35%")
if not st.session_state.signals:
    st.info("Attente d'une configuration Sniper 35% sur 70 bougies...")
else:
    for s in reversed(st.session_state.signals):
        with st.expander(f"{s['text'].splitlines()[0]} - {s['time']}", expanded=True):
            st.markdown(s['text'])

st.sidebar.subheader("📜 Logs Système")
for log in st.session_state.logs: st.sidebar.write(log)

time.sleep(30)
st.rerun()
