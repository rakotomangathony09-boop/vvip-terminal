import streamlit as st
import json, requests, websocket, threading, time, os
from datetime import datetime
import pytz

# --- CONFIGURATION SYSTÈME ---
PORT = int(os.environ.get("PORT", 10000))
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = "8599110423:AAGNHybZmy16KLBWu7nn7kl-IxdqRJ95TO0"
CHAT_ID = -5259418589 
FINNHUB_TOKEN = "d6og8phr01qnu98huumgd6og8phr01qnu98huun0"
MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

st.set_page_config(page_title="Mc ANTHONIO VVIP", layout="wide")
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v10.6 Elite")

# --- INITIALISATION DES VARIABLES D'ÉTAT ---
if "signals" not in st.session_state: st.session_state.signals = []
if "signals_count" not in st.session_state: st.session_state.signals_count = 0
if "scanned_candles" not in st.session_state: st.session_state.scanned_candles = 0
if "active_trades" not in st.session_state: st.session_state.active_trades = {}
if "running" not in st.session_state: st.session_state.running = False
if "logs" not in st.session_state: st.session_state.logs = []

def add_log(msg):
    now = datetime.now(MAD_TZ).strftime('%H:%M:%S')
    st.session_state.logs.append(f"[{now}] {msg}")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.json().get("ok"): add_log("✅ Message Telegram envoyé.")
    except Exception as e: add_log(f"⚠️ Erreur: {e}")

# --- GESTIONNAIRE DE MESSAGES (6H & 21H) ---
def daily_scheduler():
    sent_6h, sent_21h = False, False
    while True:
        now = datetime.now(MAD_TZ)
        current_time = now.strftime("%H:%M")
        
        if current_time == "06:00" and not sent_6h:
            msg = "🌅 **PRÉPARATION & DISCIPLINE VVIP**\n\nBonjour l'équipe ! Le terminal est actif.\n\n💡 *Rappel de Discipline :*\nAttendez le Sniper 30%. Ne forcez aucun trade. Le succès appartient aux patients.\n\n🛡️ **Admin : RAKOTOMANGA M.A.**"
            send_telegram(msg)
            st.session_state.signals_count = 0
            sent_6h, sent_21h = True, False
        
        if current_time == "21:00" and not sent_21h:
            status = f"✅ {st.session_state.signals_count} signaux validés." if st.session_state.signals_count > 0 else "🛡️ Aucun signal (Marché protégé)."
            msg = f"🌃 **RAPPORT DU SOIR VVIP**\n\n📊 **Activité :**\n- Bougies scannés : {st.session_state.scanned_candles}\n- Résultat : {status}\n\n📖 *Discipline :*\nSavoir ne pas trader est aussi une victoire. Reposez-vous.\n\n🛡️ **Admin : RAKOTOMANGA M.A.**"
            send_telegram(msg)
            sent_21h, sent_6h = True, False
        time.sleep(30)

# --- LOGIQUE SMC SNIPER 30% ---
def run_smc_logic(candles, symbol):
    st.session_state.scanned_candles += 1
    if len(candles) < 70: return
    h, l, c = [float(x['high']) for x in candles], [float(x['low']) for x in candles], [float(x['close']) for x in candles]
    curr_p = c[-1]
    
    # Break-Even
    if symbol in st.session_state.active_trades:
        t = st.session_state.active_trades[symbol]
        if (t['type'] == "BUY" and curr_p >= t['tp1']) or (t['type'] == "SELL" and curr_p <= t['tp1']):
            send_telegram(f"🛡️ **VVIP UPDATE : {symbol}**\n✅ TP1 ATTEINT ! Sécurisez au BE.")
            del st.session_state.active_trades[symbol]

    # Analyse
    ext_h, ext_l = max(h[-70:-15]), min(l[-70:-15])
    s_h, s_l = max(h[-10:-3]), min(l[-10:-3])

    setup = None
    # Sniper 30% Buy
    if s_l < ext_l and max(h[-3:-1]) > s_h and curr_p <= s_l + ((s_h - s_l) * 0.30):
        tp2 = ext_h
        tp1 = curr_p + ((tp2 - curr_p) * 0.50)
        setup = f"🟢 **BUY {symbol}**\n📍 Entry : `{curr_p}`\n🎯 TP1 : `{round(tp1, 2)}` | TP2 : `{round(tp2, 2)}`"
        st.session_state.active_trades[symbol] = {'type': "BUY", 'entry': curr_p, 'tp1': tp1}

    # Sniper 30% Sell
    elif s_h > ext_h and min(l[-3:-1]) < s_l and curr_p >= s_h - ((s_h - s_l) * 0.30):
        tp2 = ext_l
        tp1 = curr_p - ((curr_p - tp2) * 0.50)
        setup = f"🔴 **SELL {symbol}**\n📍 Entry : `{curr_p}`\n🎯 TP1 : `{round(tp1, 2)}` | TP2 : `{round(tp2, 2)}`"
        st.session_state.active_trades[symbol] = {'type': "SELL", 'entry': curr_p, 'tp1': tp1}

    if setup and setup not in [s.split('|')[0] for s in st.session_state.signals]:
        st.session_state.signals.append(f"{setup}|{datetime.now(MAD_TZ)}")
        st.session_state.signals_count += 1
        send_telegram(f"🏛️ **Mc ANTHONIO VVIP SIGNAL**\n\n{setup}\n\n🛡️ Admin : RAKOTOMANGA M.A.")

def start_socket():
    while True:
        try:
            ws = websocket.WebSocketApp("wss://ws.binaryws.com/websockets/v3?app_id=1089",
                on_open=lambda ws: [ws.send(json.dumps({"ticks_history": s, "subscribe": 1, "count": 100, "granularity": 300, "style": "candles"})) for s in MARKETS],
                on_message=lambda ws, m: run_smc_logic(json.loads(m)['candles'], json.loads(m)['echo_req']['ticks_history']) if 'candles' in json.loads(m) else None)
            ws.run_forever()
        except: pass
        time.sleep(5)

# --- INTERFACE ---
st.sidebar.subheader("📜 Logs Système")
for log in reversed(st.session_state.logs): st.sidebar.write(log)

if st.button("🚀 LANCER LE TERMINAL v10.6 Elite"):
    st.session_state.running = True
    send_telegram("🚀 **TERMINAL Mc ANTHONIO VVIP ACTIF**\n\n✅ Analyse SMC Sniper\n✅ Rapport 6h/21h\n🛡️ Admin : RAKOTOMANGA M.A.")
    threading.Thread(target=start_socket, daemon=True).start()
    threading.Thread(target=daily_scheduler, daemon=True).start()
    st.success("Moteur et Horloge activés !")

st.subheader("🎯 Flux de Signaux")
for s in reversed(st.session_state.signals):
    st.markdown(s.split('|')[0]); st.caption(f"Validé à : {s.split('|')[1]}")
