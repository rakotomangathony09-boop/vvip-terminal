import streamlit as st
import json, requests, websocket, threading, time, os
from datetime import datetime
import pytz

# --- CONFIGURATION RENDER & RESEAU ---
# Utilisation du port 10000 par défaut pour Render
PORT = int(os.environ.get("PORT", 10000))
MAD_TZ = pytz.timezone('Indian/Antananarivo')

# --- CONFIGURATION VVIP ---
TOKEN = "8599110423:AAGNHybZmy16KLBWu7nn7kl-IxdqRJ95TO0"
# CORRECTION CRITIQUE : Format entier sans guillemets pour l'ID
CHAT_ID = -1005259418589 
FINNHUB_TOKEN = "d6og8phr01qnu98huumgd6og8phr01qnu98huun0"
MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

st.set_page_config(page_title="Mc ANTHONIO VVIP", layout="wide")
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v10.5 Elite")

# --- INITIALISATION ---
if "signals" not in st.session_state: st.session_state.signals = []
if "active_trades" not in st.session_state: st.session_state.active_trades = {}
if "prepped" not in st.session_state: st.session_state.prepped = {}
if "running" not in st.session_state: st.session_state.running = False
if "logs" not in st.session_state: st.session_state.logs = []

def add_log(msg):
    now = datetime.now(MAD_TZ).strftime('%H:%M:%S')
    st.session_state.logs.append(f"[{now}] {msg}")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        res = r.json()
        if res.get("ok"):
            add_log("✅ Telegram: Message envoyé.")
        else:
            add_log(f"❌ Telegram Error: {res.get('description')}")
    except Exception as e:
        add_log(f"⚠️ Erreur Connexion: {e}")

def get_news_bias():
    try:
        url = f"https://finnhub.io/api/v1/calendar/economic?token={FINNHUB_TOKEN}"
        events = requests.get(url, timeout=5).json().get('economicCalendar', [])
        for e in events:
            if e['country'] == 'US' and e['impact'] == 'high' and e.get('actual'):
                diff = float(e['actual']) - float(e.get('estimate', e['actual']))
                bias = "BEARISH (SELL GOLD)" if diff > 0 else "BULLISH (BUY GOLD)"
                return f"🔥 **NEWS IMPACT : {e['event']}**\n📊 Réel: `{e['actual']}`\n🎯 Biais : **{bias}**"
        return None
    except: return None

def run_smc_logic(candles, symbol):
    if len(candles) < 70: return
    h, l, c = [float(x['high']) for x in candles], [float(x['low']) for x in candles], [float(x['close']) for x in candles]
    curr_p = c[-1]
    
    # --- GESTION DU BREAK-EVEN (BE) ---
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
    if st.session_state.prepped.get(symbol) == "BUY" and max(h[-3:-1]) > s_h and curr_p <= s_l + ((s_h - s_l) * 0.30):
        sl = s_l - abs(s_l * 0.0001)
        tp2 = ext_h
        tp1 = curr_p + ((tp2 - curr_p) * 0.50)
        setup = f"🟢 **BUY {symbol}**\n📍 Entry : `{curr_p}`\n🎯 TP1 (50%) : `{round(tp1, 2)}` | TP2 : `{round(tp2, 2)}` \n🛡️ SL : `{round(sl, 2)}`"
        st.session_state.active_trades[symbol] = {'type': "BUY", 'entry': curr_p, 'tp1': tp1}

    elif st.session_state.prepped.get(symbol) == "SELL" and min(l[-3:-1]) < s_l and curr_p >= s_h - ((s_h - s_l) * 0.30):
        sl = s_h + abs(s_h * 0.0001)
        tp2 = ext_l
        tp1 = curr_p - ((curr_p - tp2) * 0.50)
        setup = f"🔴 **SELL {symbol}**\n📍 Entry : `{curr_p}`\n🎯 TP1 (50%) : `{round(tp1, 2)}` | TP2 : `{round(tp2, 2)}` \n🛡️ SL : `{round(sl, 2)}`"
        st.session_state.active_trades[symbol] = {'type': "SELL", 'entry': curr_p, 'tp1': tp1}

    if setup and setup not in [s.split('|')[0] for s in st.session_state.signals]:
        now_t = datetime.now(MAD_TZ).strftime("%H:%M:%S")
        st.session_state.signals.append(f"{setup} | {now_t}")
        news = get_news_bias() if symbol == "frxXAUUSD" else None
        msg = f"🏛️ **Mc ANTHONIO VVIP SIGNAL**\n\n{setup}"
        if news: msg += f"\n\n{news}"
        send_telegram(msg + f"\n\n📍 Heure : {now_t}\n🛡️ Admin : RAKOTOMANGA M.A.")
        if symbol in st.session_state.prepped: del st.session_state.prepped[symbol]

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

if st.button("🚀 LANCER LE TERMINAL v10.5 Elite", disabled=st.session_state.running):
    st.session_state.running = True
    send_telegram("🚀 **TERMINAL Mc ANTHONIO VVIP EN LIGNE**\n\n✅ Stratégie : Sniper 30% / SMC\n✅ Gestion : BE au TP1 (50% Liquidité)\n🛡️ Admin : RAKOTOMANGA M.A.")
    threading.Thread(target=start_socket, daemon=True).start()
    st.success("Moteur Elite activé. Surveillez votre groupe Telegram !")

st.subheader("🎯 Flux de Signaux")
for s in reversed(st.session_state.signals):
    st.markdown(s.split('|')[0]); st.caption(f"Validé à : {s.split('|')[1]}")
