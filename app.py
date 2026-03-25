import streamlit as st
import json, requests, threading, time, os
from datetime import datetime
import pytz

# --- CONFIGURATION (Variables d'environnement Render) ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

st.set_page_config(page_title="Mc ANTHONIO VVIP Elite", layout="wide", page_icon="🏛️")

# --- MOTEUR DE PERSISTANCE (Empêche le reset à 0) ---
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
        self.logs = [f"[{now}] {msg}"] + self.logs[:12]

@st.cache_resource
def get_engine():
    return VVIPEngine()

engine = get_engine()

# --- FONCTIONS DE COMMUNICATION ---
def send_tg(msg):
    if TOKEN and CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                           json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
        except: pass

# --- LOGIQUE SMC SNIPER 35% (ANALYSE PRIX ACTUEL) ---
def analyze_market(symbol):
    try:
        # Récupération des 70 dernières bougies via API REST (Ultra-stable sur Render)
        url = f"https://api.deriv.com/api/v3/ticks?ticks={symbol}&count=70"
        res = requests.get(url, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            if 'ticks' in data:
                prices = [float(t['quote']) for t in data['ticks']]
                curr_p = prices[-1] # PRIX ACTUEL
                
                # Calcul Structure Sniper
                ext_h, ext_l = max(prices[:-15]), min(prices[:-15])
                s_h, s_l = max(prices[-12:-3]), min(prices[-12:-3])

                setup = None
                # BUY 35%
                if s_l < ext_l and max(prices[-3:-1]) > s_h and curr_p <= s_l + ((s_h - s_l) * 0.35):
                    tp2 = ext_h
                    setup = f"🟢 **BUY {symbol}**\n📍 Entrée : `{curr_p}`\n🎯 TP Final : `{round(tp2, 2)}`"
                
                # SELL 35%
                elif s_h > ext_h and min(prices[-3:-1]) < s_l and curr_p >= s_h - ((s_h - s_l) * 0.35):
                    tp2 = ext_l
                    setup = f"🔴 **SELL {symbol}**\n📍 Entrée : `{curr_p}`\n🎯 TP Final : `{round(tp2, 2)}`"

                if setup:
                    sig_id = f"{symbol}_{curr_p}"
                    if sig_id not in [s.get('id') for s in engine.signals[-5:]]:
                        t_now = datetime.now(MAD_TZ).strftime('%H:%M')
                        engine.signals.append({"id": sig_id, "text": setup, "time": t_now})
                        engine.signals_count += 1
                        send_tg(f"🏛️ **Mc ANTHONIO VVIP SIGNAL**\n\n{setup}\n🛡️ Admin : Mc ANTHONIO")
            
            engine.scanned += 1
            if engine.scanned % 12 == 0:
                engine.add_log(f"✅ Cycle complet réussi ({engine.scanned} scans)")
    except Exception as e:
        engine.add_log(f"⚠️ Erreur {symbol}: Connexion limitée")

# --- BOUCLE DE FOND (TURBO-FETCH) ---
def background_engine():
    while True:
        for m in MARKETS:
            analyze_market(m)
            time.sleep(1) # Évite la surcharge
        
        # Gestion des messages automatiques
        now = datetime.now(MAD_TZ)
        cur_t, cur_d = now.strftime("%H:%M"), now.strftime("%Y-%m-%d")
        
        if cur_t == "06:00" and engine.last_6h != cur_d:
            send_tg("🌅 **MOTIVATION VVIP**\n\nFocus et Sniper 35%. Le terminal est prêt.\n🛡️ **Mc ANTHONIO**")
            engine.last_6h = cur_d
            engine.signals_count = 0
            
        if cur_t == "21:00" and engine.last_21h != cur_d:
            send_tg(f"🌃 **RAPPORT DU SOIR**\n\n📊 Scans : {engine.scanned}\n✅ Signaux : {engine.signals_count}")
            engine.last_21h = cur_d

        time.sleep(30) # Pause entre les cycles d'analyse

# --- INITIALISATION ---
if not engine.is_running:
    threading.Thread(target=background_engine, daemon=True).start()
    engine.is_running = True
    send_tg("🏛️ **Mc ANTHONIO VVIP : SYSTÈME DÉPLOYÉ v10.8**")

# --- INTERFACE UTILISATEUR ---
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v10.8 Elite")

c1, c2, c3 = st.columns(3)
c1.metric("Moteur Status", "OPÉRATIONNEL (REST)")
c2.metric("Signaux du Jour", engine.signals_count)
c3.metric("Scans Actifs", engine.scanned)

st.divider()

col_main, col_side = st.columns([2, 1])

with col_main:
    st.subheader("📊 Signaux Sniper 35%")
    if not engine.signals:
        st.info("Surveillance de l'Or et des Indices... Le compteur de scans confirme l'activité en temps réel.")
    for s in reversed(engine.signals):
        with st.expander(f"{s['text'].splitlines()[0]} - {s['time']}", expanded=True):
            st.markdown(s['text'])

with col_side:
    st.subheader("📜 Console de Diagnostic")
    for l in engine.logs:
        st.code(l)
    if st.button("🔄 Rafraîchir l'écran"):
        st.rerun()

# Auto-refresh de l'interface
time.sleep(15)
st.rerun()
