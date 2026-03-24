import streamlit as st
import json, requests, websocket, threading, time, os
from datetime import datetime
import pytz

# --- CONFIGURATION SYSTÈME ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = "8599110423:AAGNHybZmy16KLBWu7nn7kl-IxdqRJ95TO0"
CHAT_ID = -5259418589 
FINNHUB_TOKEN = "d6og8phr01qnu98huumgd6og8phr01qnu98huun0"
MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]
APP_URL = "https://vvip-terminal-9-9.onrender.com"

st.set_page_config(page_title="Mc ANTHONIO VVIP", layout="wide")
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v10.8 Elite")

# --- INITIALISATION ---
if "signals" not in st.session_state: st.session_state.signals = []
if "signals_count" not in st.session_state: st.session_state.signals_count = 0
if "scanned_candles" not in st.session_state: st.session_state.scanned_candles = 0
if "running" not in st.session_state: st.session_state.running = False
if "logs" not in st.session_state: st.session_state.logs = []

def add_log(msg):
    now = datetime.now(MAD_TZ).strftime('%H:%M:%S')
    new_entry = f"[{now}] {msg}"
    st.session_state.logs.append(new_entry)
    print(f"ST-LOG: {new_entry}") # Pour voir dans Render "Live Tail"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

# --- SÉCURITÉ 1 : SELF-PING ANTI-SOMMEIL ---
def keep_alive():
    while True:
        try:
            requests.get(APP_URL, timeout=10)
            print("DEBUG: Self-ping réussi. Moteur actif.")
        except: pass
        time.sleep(300) # Toutes les 5 minutes

# --- SÉCURITÉ 2 : SCHEDULER ROBUSTE (Fenêtre 2 min) ---
def daily_scheduler():
    last_sent_date_6h = ""
    last_sent_date_21h = ""
    while True:
        now = datetime.now(MAD_TZ)
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")
        
        # Message 06h00
        if "06:00" <= current_time <= "06:02" and last_sent_date_6h != current_date:
            msg = "🌅 **PRÉPARATION & DISCIPLINE VVIP**\n\nBonjour l'équipe ! Le terminal est actif.\n💡 Attendez le Sniper 30%.\n\n🛡️ **Admin : Mc ANTHONIO**"
            send_telegram(msg)
            st.session_state.signals_count = 0
            last_sent_date_6h = current_date
        
        # Message 21h00
        if "21:00" <= current_time <= "21:02" and last_sent_date_21h != current_date:
            status = f"✅ {st.session_state.signals_count} signaux validés." if st.session_state.signals_count > 0 else "🛡️ Aucun signal (Marché protégé)."
            msg = f"🌃 **RAPPORT DU SOIR VVIP**\n\n📊 **Activité :**\n- Bougies scannées : {st.session_state.scanned_candles}\n- Résultat : {status}\n\n🛡️ **Admin : Mc ANTHONIO**"
            send_telegram(msg)
            last_sent_date_21h = current_date
            
        time.sleep(30)

# --- ANALYSE SMC SNIPER 30% ---
def run_smc_logic(candles, symbol):
    st.session_state.scanned_candles += 1
    if len(candles) < 70: return
    h, l, c = [float(x['high']) for x in candles], [float(x['low']) for x in candles], [float(x['close']) for x in candles]
    curr_p = c[-1]
    
    ext_h, ext_l = max(h[-70:-15]), min(l[-70:-15])
    s_h, s_l = max(h[-10:-3]), min(l[-10:-3])

    setup = None
    if s_l < ext_l and max(h[-3:-1]) > s_h and curr_p <= s_l + ((s_h - s_l) * 0.30):
        tp2, tp1 = ext_h, curr_p + ((ext_h - curr_p) * 0.50)
        setup = f"🟢 **BUY {symbol}**\n📍 Entry : `{curr_p}`\n🎯 TP1 : `{round(tp1, 2)}` | TP2 : `{round(tp2, 2)}`"
    elif s_h > ext_h and min(l[-3:-1]) < s_l and curr_p >= s_h - ((s_h - s_l) * 0.30):
        tp2, tp1 = ext_l, curr_p - ((curr_p - ext_l) * 0.50)
        setup = f"🔴 **SELL {symbol}**\n📍 Entry : `{curr_p}`\n🎯 TP1 : `{round(tp1, 2)}` | TP2 : `{round(tp2, 2)}`"

    if setup and setup not in [s.split('|')[0] for s in st.session_state.signals]:
        st.session_state.signals.append(f"{setup}|{datetime.now(MAD_TZ).strftime('%H:%M')}")
        st.session_state.signals_count += 1
        send_telegram(f"🏛️ **Mc ANTHONIO VVIP SIGNAL**\n\n{setup}\n🛡️ Admin : Mc ANTHONIO")

def start_socket():
    while True:
        try:
            ws = websocket.WebSocketApp("wss://ws.binaryws.com/websockets/v3?app_id=1089",
                on_open=lambda ws: [ws.send(json.dumps({"ticks_history": s, "subscribe": 1, "count": 100, "granularity": 300, "style": "candles"})) for s in MARKETS],
                on_message=lambda ws, m: run_smc_logic(json.loads(m)['candles'], json.loads(m)['echo_req']['ticks_history']) if 'candles' in json.loads(m) else None)
            ws.run_forever()
        except: time.sleep(5)

# --- SÉCURITÉ 3 : AUTO-START INTERFACE ---
st.sidebar.subheader("📜 Logs Système")
for log in reversed(st.session_state.logs): st.sidebar.write(log)

if not st.session_state.running:
    st.session_state.running = True
    add_log("🚀 Moteur v10.8 activé...")
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=start_socket, daemon=True).start()
    threading.Thread(target=daily_scheduler, daemon=True).start()
    send_telegram("🏛️ **Mc ANTHONIO VVIP : MOTEUR ULTRA-STABLE ACTIF**\n\n✅ Anti-Sommeil activé\n✅ Auto-Start OK\n🛡️ Admin : Mc ANTHONIO")

st.success("✅ Terminal en ligne. Scan actif.")
