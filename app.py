import streamlit as st
import json, requests, websocket, threading, time
from datetime import datetime
import pytz

# --- CONFIGURATION VVIP ---
TOKEN = "8599110423:AAGNHybZmy16KLBWu7nn7kl-IxdqRJ95TO0"
CHAT_ID = "-5259418589" 
FINNHUB_TOKEN = "d6og8phr01qnu98huumgd6og8phr01qnu98huun0"
MAD_TZ = pytz.timezone('Indian/Antananarivo')
MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

st.set_page_config(page_title="Mc ANTHONIO VVIP", layout="wide")
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v10.5 Elite")

# --- INITIALISATION ---
if "signals" not in st.session_state: st.session_state.signals = []
if "active_trades" not in st.session_state: st.session_state.active_trades = {}
if "prepped" not in st.session_state: st.session_state.prepped = {}
if "running" not in st.session_state: st.session_state.running = False
if "activity_log" not in st.session_state: st.session_state.activity_log = {}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def run_smc_logic(candles, symbol):
    st.session_state.activity_log[symbol] = st.session_state.activity_log.get(symbol, 0) + 1
    if len(candles) < 70: return
    h, l, c = [float(x['high']) for x in candles], [float(x['low']) for x in candles], [float(x['close']) for x in candles]
    curr_p = c[-1]
    
    # --- GESTION DU BE (BREAK-EVEN) ---
    if symbol in st.session_state.active_trades:
        t = st.session_state.active_trades[symbol]
        if (t['type'] == "BUY" and curr_p >= t['tp1']) or (t['type'] == "SELL" and curr_p <= t['tp1']):
            send_telegram(f"🛡️ **VVIP UPDATE : {symbol}**\n\n✅ **TP1 (50% Liquidity) ATTEINT !**\n🚀 Sécurisez : Placez votre SL au **Break-Even (BE)**.\n📍 Nouveau SL : `{t['entry']}`")
            del st.session_state.active_trades[symbol]

    # --- ANALYSE SMC ---
    ext_h, ext_l = max(h[-70:-15]), min(l[-70:-15])
    s_h, s_l = max(h[-10:-3]), min(l[-10:-3])

    if s_l < ext_l: st.session_state.prepped[symbol] = "BUY"
    elif s_h > ext_h: st.session_state.prepped[symbol] = "SELL"

    setup = None
    # BUY : TP2 = Liquidité finale (ext_h), TP1 = 50% entre Entry et ext_h
    if st.session_state.prepped.get(symbol) == "BUY" and max(h[-3:-1]) > s_h and curr_p <= s_l + ((s_h - s_l) * 0.30):
        sl = s_l - abs(s_l * 0.0001)
        tp2 = ext_h
        tp1 = curr_p + ((tp2 - curr_p) * 0.50) # 50% de la distance
        setup = f"🟢 **BUY {symbol}**\n📍 Entry : `{curr_p}`\n🎯 TP1 (50%) : `{round(tp1, 2)}`\n🎯 TP2 (Final) : `{round(tp2, 2)}` \n🛡️ SL : `{round(sl, 2)}`"
        st.session_state.active_trades[symbol] = {'type': "BUY", 'entry': curr_p, 'tp1': tp1}

    # SELL : TP2 = Liquidité finale (ext_l), TP1 = 50% entre Entry et ext_l
    elif st.session_state.prepped.get(symbol) == "SELL" and min(l[-3:-1]) < s_l and curr_p >= s_h - ((s_h - s_l) * 0.30):
        sl = s_h + abs(s_h * 0.0001)
        tp2 = ext_l
        tp1 = curr_p - ((curr_p - tp2) * 0.50) # 50% de la distance
        setup = f"🔴 **SELL {symbol}**\n📍 Entry : `{curr_p}`\n🎯 TP1 (50%) : `{round(tp1, 2)}`\n🎯 TP2 (Final) : `{round(tp2, 2)}` \n🛡️ SL : `{round(sl, 2)}`"
        st.session_state.active_trades[symbol] = {'type': "SELL", 'entry': curr_p, 'tp1': tp1}

    if setup and setup not in [s.split('|')[0] for s in st.session_state.get("signals", [])]:
        now_t = datetime.now(MAD_TZ).strftime("%H:%M:%S")
        st.session_state.signals.append(f"{setup} | {now_t}")
        send_telegram(f"🏛️ **Mc ANTHONIO VVIP SIGNAL**\n\n{setup}\n\n📍 Heure : {now_t}\n🛡️ Admin : RAKOTOMANGA M.A.")
        if symbol in st.session_state.prepped: del st.session_state.prepped[symbol]

# --- FONCTIONS DE LANCEMENT ---
def start_socket():
    while True:
        try:
            ws = websocket.WebSocketApp("wss://ws.binaryws.com/websockets/v3?app_id=1089",
                on_open=lambda ws: [ws.send(json.dumps({"ticks_history": s, "subscribe": 1, "count": 100, "granularity": 300, "style": "candles"})) for s in MARKETS],
                on_message=lambda ws, m: run_smc_logic(json.loads(m)['candles'], json.loads(m)['echo_req']['ticks_history']) if 'candles' in json.loads(m) else None)
            ws.run_forever()
        except: pass
        time.sleep(5)

if st.button("🚀 LANCER LE TERMINAL v10.5"):
    st.session_state.running = True
    threading.Thread(target=start_socket, daemon=True).start()
    st.success("Moteur Elite avec TP1 à 50% de la liquidité activé !")
