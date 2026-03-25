import streamlit as st
import json, requests, threading, time, os, websocket
from datetime import datetime
import pytz

# --- CONFIGURATION ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
# Liste de test pour débloquer (on surveille 12 marchés)
MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

st.set_page_config(page_title="Mc ANTHONIO VVIP v11.0 Elite", layout="wide", page_icon="🏛️")

# --- MÉMOIRE PERSISTANTE ---
class VVIPEngine:
    def __init__(self):
        self.scanned = 0
        self.signals = []
        self.logs = []
        self.is_running = False
        # Drapeau de sécurité pour éviter le spam (verrouillage)
        self.start_message_sent = False

    def add_log(self, msg):
        now = datetime.now(MAD_TZ).strftime('%H:%M:%S')
        self.logs = [f"[{now}] {msg}"] + self.logs[:12]

@st.cache_resource
def get_engine(): return VVIPEngine()
engine = get_engine()

def send_tg(msg):
    if TOKEN and CHAT_ID:
        try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                           json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
        except: pass

# --- CŒUR DU SCANNER (Force Brute) ---
def fetch_and_analyze(symbol):
    try:
        # Connexion courte "One-Shot" ultra-stable sur Render
        ws = websocket.create_connection("wss://ws.binaryws.com/websockets/v3?app_id=1089", timeout=10)
        ws.send(json.dumps({"ticks_history": symbol, "count": 70, "style": "candles", "granularity": 300}))
        result = json.loads(ws.recv())
        ws.close()

        if 'candles' in result:
            prices = [float(c['close']) for c in result['candles']]
            highs = [float(c['high']) for c in result['candles']]
            lows = [float(c['low']) for c in result['candles']]
            curr_p = prices[-1]

            # --- LOGIQUE SMC SNIPER 35% (v11.0 Elite) ---
            ext_h, ext_l = max(highs[:-15]), min(lows[:-15])
            s_h, s_l = max(highs[-12:-3]), min(lows[-12:-3])

            setup = None
            if s_l < ext_l and max(highs[-3:-1]) > s_h and curr_p <= s_l + ((s_h - s_l) * 0.35):
                sl = s_l - ((s_h - s_l) * 0.15)
                tp = ext_h
                setup = f"🟢 **BUY {symbol}** (SMC Sniper 35%)\n📍 Entrée : `{curr_p}`\n🛡️ SL : `{round(sl, 2)}` | 🏆 TP : `{round(tp, 2)}`"
            elif s_h > ext_h and min(lows[-3:-1]) < s_l and curr_p >= s_h - ((s_h - s_l) * 0.35):
                sl = s_h + ((s_h - s_l) * 0.15)
                tp = ext_l
                setup = f"🔴 **SELL {symbol}** (SMC Sniper 35%)\n📍 Entrée : `{curr_p}`\n🛡️ SL : `{round(sl, 2)}` | 🏆 TP : `{round(tp, 2)}`"

            if setup:
                sig_id = f"{symbol}_{curr_p}"
                if sig_id not in [s.get('id', '') for s in engine.signals]:
                    t_now = datetime.now(MAD_TZ).strftime('%H:%M')
                    engine.signals.append({"id": sig_id, "text": setup, "time": t_now})
                    send_tg(f"🏛️ **Mc ANTHONIO VVIP SIGNAL**\n\n{setup}")

            engine.scanned += 1
            if engine.scanned % 12 == 0:
                engine.add_log(f"✅ Scan actif sur {symbol}")
    except:
        engine.add_log(f"❌ Erreur réseau {symbol}")

def force_loop():
    while True:
        for m in MARKETS:
            fetch_and_analyze(m)
            time.sleep(2)
        time.sleep(10)

if not engine.is_running:
    threading.Thread(target=force_loop, daemon=True).start()
    engine.is_running = True
    # send_tg(removed spam source) - Le message n'est plus envoyé ici

# --- INTERFACE ---
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v11.0")

col1, col2, col3 = st.columns(3)
col1.metric("Moteur", "OPÉRATIONNEL (STABLE)")
col2.metric("Signaux Valides", len(engine.signals))
col3.metric("Scans Actifs", engine.scanned)

# --- CORRECTIF : ENVOI DU MESSAGE UNE SEULE FOIS ---
# Ce bloc ne s'active que SI AU MOINS UN SCAN A RÉUSSI et QUE LE MESSAGE N'A PAS ÉTÉ ENVOYÉ.
if engine.scanned > 0 and not engine.start_message_sent:
    time_now = datetime.now(MAD_TZ).strftime('%H:%M')
    send_tg(f"🏛️ **Mc ANTHONIO VVIP : TERMINAL v11.0 EN LIGNE**\n✅ Moteur : Stable & Actif\nScans actifs : {engine.scanned}\n🛡️ Admin : Mc ANTHONIO")
    # Verrouillage : Cette session ne renverra plus ce message.
    engine.start_message_sent = True

st.divider()
c_left, c_right = st.columns([2, 1])

with c_left:
    st.subheader("📊 Derniers Signaux Institutionnels 35%")
    if not engine.signals: st.info("Analyse en cours... Attente d'une configuration Sniper.")
    for s in reversed(engine.signals): st.success(f"🕙 {s['time']} | {s['text']}")

with c_right:
    st.subheader("📜 Diagnostic")
    for l in engine.logs: st.code(l)
    if st.button("🔄 Rafraîchir l'écran"): st.rerun()

# Auto-refresh de l'interface
time.sleep(15)
st.rerun()
