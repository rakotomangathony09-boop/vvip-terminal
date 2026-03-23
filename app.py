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
st.title("🏛️ Mc ANTHONIO VVIP - ICT Terminal v9.9")
st.caption("Stratégie : Sweep + BOS + Pullback | SL 50% Sweep | TP2 Next Liquidity")

if "signals" not in st.session_state:
    st.session_state.signals = []

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def run_smc_logic(candles, symbol):
    if len(candles) < 70: return
    closes = [float(c['close']) for c in candles]
    highs = [float(c['high']) for c in candles]
    lows = [float(c['low']) for c in candles]
    
    curr_p = closes[-1]
    # Zone de liquidité externe et structure interne
    external_h, external_l = max(highs[-70:-15]), min(lows[-70:-15])
    internal_h, internal_l = max(highs[-15:-5]), min(lows[-15:-5])
    
    setup = None
    now_t = datetime.now(MAD_TZ).strftime("%H:%M:%S")

    # --- LOGIQUE ACHAT (BUY) ---
    s_b_h, s_b_l = max(highs[-10:-3]), min(lows[-10:-3])
    if s_b_l < external_l and max(highs[-3:-1]) > s_b_h and curr_p <= s_b_l + ((s_b_h - s_b_l) * 0.3):
        sl = s_b_l + ((s_b_h - s_b_l) * 0.5) 
        tp1 = internal_l + ((internal_h - internal_l) * 0.5)
        tp2 = external_h 
        if curr_p >= tp1: tp1 = curr_p + abs(curr_p - sl) * 0.5
        setup = f"🟢 **BUY {symbol} (ICT Setup)**\n📍 Entrée : `{curr_p}`\n🎯 TP1 (50% Int) : `{round(tp1, 2)}`\n💎 TP2 (Next Liq) : `{round(tp2, 2)}`\n🛡️ SL (50% Sweep) : `{round(sl, 2)}`"

    # --- LOGIQUE VENTE (SELL) ---
    s_s_h, s_s_l = max(highs[-10:-3]), min(lows[-10:-3])
    if s_s_h > external_h and min(lows[-3:-1]) < s_s_l and curr_p >= s_s_h - ((s_s_h - s_s_l) * 0.3):
        sl = s_s_h - ((s_s_h - s_s_l) * 0.5)
        tp1 = internal_h - ((internal_h - internal_l) * 0.5)
        tp2 = external_l
        if curr_p <= tp1: tp1 = curr_p - abs(sl - curr_p) * 0.5
        setup = f"🔴 **SELL {symbol} (ICT Setup)**\n📍 Entrée : `{curr_p}`\n🎯 TP1 (50% Int) : `{round(tp1, 2)}`\n💎 TP2 (Next Liq) : `{round(tp2, 2)}`\n🛡️ SL (50% Sweep) : `{round(sl, 2)}`"

    if setup and (setup not in [s.split('|')[0] for s in st.session_state.signals]):
        st.session_state.signals.append(f"{setup} | {now_t}")
        send_telegram(f"🏛️ **Mc ANTHONIO VVIP SIGNAL**\n\n{setup}\n\n📍 Heure : {now_t}\n🛡️ Admin : RAKOTOMANGA M.A.")

def start_socket():
    ws = websocket.WebSocketApp("wss://ws.binaryws.com/websockets/v3?app_id=1089",
        on_open=lambda ws: [ws.send(json.dumps({"ticks_history": s, "subscribe": 1, "count": 100, "granularity": 300, "style": "candles"})) for s in MARKETS],
        on_message=lambda ws, m: run_smc_logic(json.loads(m)['candles'], json.loads(m)['echo_req']['ticks_history']) if 'candles' in json.loads(m) else None)
    ws.run_forever()

# --- INTERFACE ---
col1, col2 = st.columns([1, 2])
with col1:
    if st.button("🚀 LANCER LE SCANNER ICT"):
        threading.Thread(target=start_socket, daemon=True).start()
        st.success("Moteur ICT Actif")
        send_telegram("🏛️ **Mc ANTHONIO VVIP v9.9**\n🚀 Système en ligne.\n📊 Stratégie ICT/SMC activée.")
with col2:
    st.subheader("🎯 Flux de Signaux")
    for s in reversed(st.session_state.signals[-15:]):
        st.markdown(s.split('|')[0])
        st.caption(f"Détecté à : {s.split('|')[1]}")
