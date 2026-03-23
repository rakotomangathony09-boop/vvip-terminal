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
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v9.9 Pro")

# --- INITIALISATION SESSION ---
if "signals" not in st.session_state: st.session_state.signals = []
if "prepped" not in st.session_state: st.session_state.prepped = {}
if "running" not in st.session_state: st.session_state.running = False
if "activity_log" not in st.session_state: st.session_state.activity_log = {} # Nouveau : Suivi par actif

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def routine_tasks():
    while True:
        now = datetime.now(MAD_TZ).strftime("%H:%M")
        
        # 🌅 MATIN (06:00)
        if now == "06:00":
            send_telegram("🏛️ **Mc ANTHONIO VVIP - SESSION OUVERTE**\n\n🌅 *Statut :* Moteur Sniper v9.9 en ligne.\n🔍 *Cible :* Gold + 18 Synthétiques.\n🛡️ Admin : RAKOTOMANGA M.A.")
            time.sleep(70)
        
        # 📊 BILAN DU SOIR (21:00) - RAPPORT D'ACTIVITÉ TOTAL
        if now == "21:00":
            signals_list = st.session_state.get("signals", [])
            activity = st.session_state.get("activity_log", {})
            
            report = "📊 **RAPPORT D'ACTIVITÉ JOURNALIER**\n\n"
            
            # 1. Résumé des Scans
            report += "🔍 **Analyse des Marchés :**\n"
            if activity:
                for market, count in activity.items():
                    report += f"• `{market}` : {count} bougies analysées\n"
            else:
                report += "• Aucun flux de données détecté.\n"

            report += "\n🎯 **Résultats Sniper :**\n"
            # 2. Résumé des Signaux
            if len(signals_list) > 0:
                report += f"✅ {len(signals_list)} Opportunités validées :\n"
                for s in signals_list:
                    parts = s.split('|')
                    title = parts[0].split('\n')[0].replace('🟢 ', '').replace('🔴 ', '')
                    report += f"  └ {parts[1].strip()} : {title}\n"
            else:
                report += "⚠️ *Aucune confluence parfaite détectée aujourd'hui. Discipline respectée : Pas de signal forcé.*"
            
            report += "\n\n🛡️ Admin : RAKOTOMANGA M.A."
            send_telegram(report)
            
            # Reset optionnel de l'activité pour le lendemain
            st.session_state.activity_log = {}
            time.sleep(70)
        time.sleep(30)

def run_smc_logic(candles, symbol):
    # Initialisation de la mémoire si crash
    if "signals" not in st.session_state: st.session_state.signals = []
    if "activity_log" not in st.session_state: st.session_state.activity_log = {}
    
    # --- ENREGISTREMENT DE L'ACTIVITÉ ---
    # On incrémente le compteur de scan pour cet actif
    st.session_state.activity_log[symbol] = st.session_state.activity_log.get(symbol, 0) + 1

    if len(candles) < 70: return
    h, l, c = [float(x['high']) for x in candles], [float(x['low']) for x in candles], [float(x['close']) for x in candles]
    curr_p = c[-1]
    ext_h, ext_l = max(h[-70:-15]), min(l[-70:-15])
    s_h, s_l = max(h[-10:-3]), min(l[-10:-3])
    now_t = datetime.now(MAD_TZ).strftime("%H:%M:%S")

    # LOGIQUE SMC (Sweep -> BOS -> Entry)
    if s_l < ext_l and symbol not in st.session_state.prepped:
        st.session_state.prepped[symbol] = "BUY"
    elif s_h > ext_h and symbol not in st.session_state.prepped:
        st.session_state.prepped[symbol] = "SELL"

    setup = None
    if st.session_state.prepped.get(symbol) == "BUY" and max(h[-3:-1]) > s_h and curr_p <= s_l + ((s_h - s_l) * 0.45):
        sl = s_l - abs(s_l * 0.0001); tp1, tp2 = curr_p + abs(curr_p - sl), ext_h
        setup = f"🟢 **BUY {symbol}**\n📍 Entry : `{curr_p}`\n🎯 TP1 : `{round(tp1, 2)}` | TP2 : `{round(tp2, 2)}` \n🛡️ SL : `{round(sl, 2)}`"

    elif st.session_state.prepped.get(symbol) == "SELL" and min(l[-3:-1]) < s_l and curr_p >= s_h - ((s_h - s_l) * 0.45):
        sl = s_h + abs(s_h * 0.0001); tp1, tp2 = curr_p - abs(sl - curr_p), ext_l
        setup = f"🔴 **SELL {symbol}**\n📍 Entry : `{curr_p}`\n🎯 TP1 : `{round(tp1, 2)}` | TP2 : `{round(tp2, 2)}` \n🛡️ SL : `{round(sl, 2)}`"

    if setup and setup not in [s.split('|')[0] for s in st.session_state.signals]:
        st.session_state.signals.append(f"{setup} | {now_t}")
        send_telegram(f"🏛️ **Mc ANTHONIO VVIP SIGNAL**\n\n{setup}\n\n📍 Heure : {now_t}\n🛡️ Admin : RAKOTOMANGA M.A.")
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
if st.button("🚀 LANCER LE SYSTÈME VVIP v9.9", disabled=st.session_state.running):
    st.session_state.running = True
    threading.Thread(target=start_socket, daemon=True).start()
    threading.Thread(target=routine_tasks, daemon=True).start()
    st.success("Moteur Sniper v9.9 avec Journal de Bord activé !")

st.subheader("🎯 Signaux de la session")
for s in reversed(st.session_state.get("signals", [])):
    st.markdown(s.split('|')[0]); st.caption(f"Validé à : {s.split('|')[1]}")
