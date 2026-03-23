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
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v9.9")

if "signals" not in st.session_state: st.session_state.signals = []
if "prepped" not in st.session_state: st.session_state.prepped = {}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

# --- ANALYSEUR DE NEWS (DATA RÉELLE) ---
def analyze_news_impact():
    try:
        url = f"https://finnhub.io/api/v1/calendar/economic?token={FINNHUB_TOKEN}"
        events = requests.get(url, timeout=5).json().get('economicCalendar', [])
        for e in events:
            if e['country'] == 'US' and e['impact'] == 'high' and e.get('actual') is not None:
                actual, estimate = float(e['actual']), float(e.get('estimate', e['actual']))
                diff = actual - estimate
                direction = "🚀 USD BULLISH (SELL GOLD)" if diff > 0 else "📉 USD BEARISH (BUY GOLD)"
                return f"📊 **DATA NEWS RÉELLE : {e['event']}**\n✅ Actuel : `{actual}` | Prévu : `{estimate}`\n💡 Impact : {direction}"
        return None
    except: return None

# --- MESSAGES AUTOMATIQUES (06:00 / 21:00) ---
def routine_tasks():
    while True:
        now = datetime.now(MAD_TZ).strftime("%H:%M")
        if now == "06:00":
            send_telegram("🏛️ **Mc ANTHONIO VVIP - BONJOUR**\n\n🌅 *Préparation :* Scanner v9.9 actif. 12 marchés sous surveillance.\n🔥 *Motivation :* La discipline est le pont entre vos buts et vos accomplissements.\n🛡️ Admin : RAKOTOMANGA M.A.")
            time.sleep(70)
        if now == "21:00":
            nb = len(st.session_state.signals)
            report = f"📊 *Bilan :* {nb} signaux validés." if nb > 0 else "📊 *Bilan :* Aucun signal validé (Patience = Profit)."
            send_telegram(f"🏛️ **Mc ANTHONIO VVIP - SOIR**\n\n✨ *Motivation :* Une journée de plus vers la liberté. Reposez-vous.\n{report}\n🛡️ Admin : RAKOTOMANGA M.A.")
            time.sleep(70)
        time.sleep(30)

# --- LOGIQUE SMC (SWEEP -> PREP | BOS + PULLBACK -> SIGNAL) ---
def run_smc_logic(candles, symbol):
    if len(candles) < 70: return
    h, l, c = [float(x['high']) for x in candles], [float(x['low']) for x in candles], [float(x['close']) for x in candles]
    curr_p = c[-1]
    ext_h, ext_l = max(h[-70:-15]), min(l[-70:-15])
    s_h, s_l = max(h[-10:-3]), min(l[-10:-3])
    now_t = datetime.now(MAD_TZ).strftime("%H:%M:%S")

    # 1. ÉTAPE DE PRÉPARATION (SWEEP DETECTÉ)
    if s_l < ext_l and symbol not in st.session_state.prepped:
        st.session_state.prepped[symbol] = "BUY"
        send_telegram(f"⏳ **PRÉPARATION VVIP : {symbol}**\n⚠️ Balayage de liquidité (Sweep Low). Setup d'achat en formation. Attendez le BOS.")
    
    if s_h > ext_h and symbol not in st.session_state.prepped:
        st.session_state.prepped[symbol] = "SELL"
        send_telegram(f"⏳ **PRÉPARATION VVIP : {symbol}**\n⚠️ Balayage de liquidité (Sweep High). Setup de vente en formation. Attendez le BOS.")

    # 2. ÉTAPE DE SIGNAL (BOS + PULLBACK VERS LIQUIDITÉ)
    # --- ACHAT ---
    if st.session_state.prepped.get(symbol) == "BUY" and max(h[-3:-1]) > s_h and curr_p <= s_l + ((s_h - s_l) * 0.45):
        sl = s_l - abs(s_l * 0.0001) # SL SOUS LA MÈCHE DU SWEEP
        tp1, tp2 = curr_p + abs(curr_p - sl), ext_h
        setup = f"🟢 **BUY {symbol} (SMC Setup)**\n📍 Entrée (Pullback) : `{curr_p}`\n🎯 TP1 : `{round(tp1, 2)}`\n💎 TP2 (Liq) : `{round(tp2, 2)}`\n🛡️ SL (Sous Sweep) : `{round(sl, 2)}`"
        if setup not in [s.split('|')[0] for s in st.session_state.signals]:
            st.session_state.signals.append(f"{setup} | {now_t}")
            news = analyze_news_impact() if symbol == "frxXAUUSD" else None
            msg = f"🏛️ **Mc ANTHONIO VVIP SIGNAL**\n\n{setup}"
            if news: msg += f"\n\n{news}"
            send_telegram(msg + f"\n\n📍 Heure : {now_t}\n🛡️ Admin : RAKOTOMANGA M.A.")
            del st.session_state.prepped[symbol]

    # --- VENTE ---
    if st.session_state.prepped.get(symbol) == "SELL" and min(l[-3:-1]) < s_l and curr_p >= s_h - ((s_h - s_l) * 0.45):
        sl = s_h + abs(s_h * 0.0001) # SL SUR LA MÈCHE DU SWEEP
        tp1, tp2 = curr_p - abs(sl - curr_p), ext_l
        setup = f"🔴 **SELL {symbol} (SMC Setup)**\n📍 Entrée (Pullback) : `{curr_p}`\n🎯 TP1 : `{round(tp1, 2)}`\n💎 TP2 (Liq) : `{round(tp2, 2)}`\n🛡️ SL (Sur Sweep) : `{round(sl, 2)}`"
        if setup not in [s.split('|')[0] for s in st.session_state.signals]:
            st.session_state.signals.append(f"{setup} | {now_t}")
            news = analyze_news_impact() if symbol == "frxXAUUSD" else None
            msg = f"🏛️ **Mc ANTHONIO VVIP SIGNAL**\n\n{setup}"
            if news: msg += f"\n\n{news}"
            send_telegram(msg + f"\n\n📍 Heure : {now_t}\n🛡️ Admin : RAKOTOMANGA M.A.")
            del st.session_state.prepped[symbol]

def start_socket():
    ws = websocket.WebSocketApp("wss://ws.binaryws.com/websockets/v3?app_id=1089",
        on_open=lambda ws: [ws.send(json.dumps({"ticks_history": s, "subscribe": 1, "count": 100, "granularity": 300, "style": "candles"})) for s in MARKETS],
        on_message=lambda ws, m: run_smc_logic(json.loads(m)['candles'], json.loads(m)['echo_req']['ticks_history']) if 'candles' in json.loads(m) else None)
    ws.run_forever()

if st.button("🚀 LANCER LE SYSTÈME VVIP v9.9"):
    threading.Thread(target=start_socket, daemon=True).start()
    threading.Thread(target=routine_tasks, daemon=True).start()
    st.success("Moteur v9.9 Full Option Activé !")
    send_telegram("🏛️ **Mc ANTHONIO VVIP v9.9**\n🚀 Terminal opérationnel (SMC + News Data + Auto-Messages).")

st.subheader("🎯 Flux de Signaux")
for s in reversed(st.session_state.signals):
    st.markdown(s.split('|')[0]); st.caption(f"Validé à : {s.split('|')[1]}")
