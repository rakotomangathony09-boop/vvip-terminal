import streamlit as st
import json, requests, threading, time, os, websocket
from datetime import datetime, timedelta
import pytz

# --- 1. CONFIGURATION ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FINNHUB_KEY = os.getenv("FINNHUB_TOKEN")
APP_URL = os.getenv("APP_URL") # Ton URL Render pour le Self-Ping

MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

st.set_page_config(page_title="Mc ANTHONIO VVIP v11.0 Elite", layout="wide", page_icon="🏛️")

# --- 2. MOTEUR DE DONNÉES ---
class VVIPEngine:
    def __init__(self):
        self.scanned = 0
        self.signals = []
        self.logs = []
        self.is_running = False
        self.last_motivation_day = ""
        self.last_report_hour = -1
        self.current_news = "Initialisation..."

    def add_log(self, msg):
        now = datetime.now(MAD_TZ).strftime('%H:%M:%S')
        self.logs = [f"[{now}] {msg}"] + self.logs[:10]

@st.cache_resource
def get_engine(): return VVIPEngine()
engine = get_engine()

def send_tg(msg):
    if TOKEN and CHAT_ID:
        try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                           json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
        except: pass

# --- 3. ANALYSE NEWS (FINNHUB) ---
def check_news():
    if not FINNHUB_KEY: return
    try:
        url = f"https://finnhub.io/api/v1/calendar/economic?token={FINNHUB_KEY}"
        data = requests.get(url).json().get('economicCalendar', [])
        found = False
        for event in data:
            if event['country'] == 'US' and event['impact'] == 'high':
                e_time = datetime.fromtimestamp(event['time'], tz=pytz.utc).astimezone(MAD_TZ)
                now = datetime.now(MAD_TZ)
                if now < e_time < (now + timedelta(minutes=60)):
                    engine.current_news = f"⚠️ NEWS USD : {event['event']} ({e_time.strftime('%H:%M')})"
                    found = True; break
        if not found: engine.current_news = "Normal (Pas de news majeure)"
    except: engine.current_news = "Erreur News API"

# --- 4. ANALYSE TECHNIQUE SMC (SWEEP -> BOS -> RETEST) ---
def fetch_and_analyze(symbol):
    try:
        ws = websocket.create_connection("wss://ws.binaryws.com/websockets/v3?app_id=1089", timeout=10)
        ws.send(json.dumps({"ticks_history": symbol, "count": 100, "style": "candles", "granularity": 300}))
        res = json.loads(ws.recv()); ws.close()

        if 'candles' in res:
            c = res['candles']
            h, l, cl = [float(x['high']) for x in c], [float(x['low']) for x in c], [float(x['close']) for x in c]
            curr_p = cl[-1]
            ext_h, ext_l = max(h[20:80]), min(l[20:80])

            setup = None
            # Logique BUY : Sweep Bas + BOS + Retest Zone Sweep
            rec_l = min(l[-15:])
            if rec_l < ext_l and curr_p > max(h[-12:-2]):
                if curr_p <= ext_l + (abs(ext_l - rec_l) * 0.40):
                    setup = f"🟢 **BUY SNIPER** {symbol}\n📍 Entrée (Retest Area) : `{curr_p}`\n🛡️ SL : `{round(rec_l, 2)}` | 🏆 TP : `{round(ext_h, 2)}`"

            # Logique SELL : Sweep Haut + BOS + Retest Zone Sweep
            rec_h = max(h[-15:])
            if rec_h > ext_h and curr_p < min(l[-12:-2]):
                if curr_p >= ext_h - (abs(rec_h - ext_h) * 0.40):
                    setup = f"🔴 **SELL SNIPER** {symbol}\n📍 Entrée (Retest Area) : `{curr_p}`\n🛡️ SL : `{round(rec_h, 2)}` | 🏆 TP : `{round(ext_l, 2)}`"

            if setup:
                sig_id = f"{symbol}_{round(curr_p, 2)}"
                if sig_id not in [s.get('id', '') for s in engine.signals]:
                    engine.signals.append({"id": sig_id, "text": setup, "time": datetime.now(MAD_TZ).strftime('%H:%M')})
                    send_tg(f"🏛️ **Mc ANTHONIO VVIP**\n\n{setup}\n🌐 News : {engine.current_news}\n👤 @McAnthonio")
            engine.scanned += 1
    except Exception as e:
        engine.add_log(f"Err {symbol}: {str(e)[:20]}")

# --- 5. BOUCLE DE CONTRÔLE AUTO (06H-22H) ---
def force_loop():
    engine.add_log("🚀 Moteur SMC démarré")
    while True:
        try:
            now = datetime.now(MAD_TZ)
            hr, dy, dt = now.hour, now.weekday(), now.strftime("%Y-%m-%d")

            # Update News toutes les 30 min
            if now.minute % 30 == 0: check_news()

            # Message Motivation (06:00)
            if hr == 6 and engine.last_motivation_day != dt:
                send_tg("☀️ **SESSION OUVERTE Mc ANTHONIO VVIP**\n\n🔥 *Discipline :* Attends le Retest.\nSois le sniper, pas la proie.")
                engine.last_motivation_day = dt

            # Rapports horaires (9h, 12h, 15h, 18h, 21h)
            if hr in [9, 12, 15, 18, 21] and engine.last_report_hour != hr:
                send_tg(f"📊 **RAPPORT VVIP ({hr}h)**\n✅ Scans : {engine.scanned}\n📈 Signaux : {len(engine.signals)}\n👤 @McAnthonio")
                engine.last_report_hour = hr

            # Scan Actif
            if 6 <= hr < 22:
                for m in MARKETS:
                    if m == "frxXAUUSD" and dy >= 5: continue
                    fetch_and_analyze(m)
                    time.sleep(2.2) # Sécurité Render
            else:
                time.sleep(60) # Mode nuit
            
            # Anti-Sommeil
            if APP_URL and now.minute % 10 == 0:
                try: requests.get(APP_URL, timeout=5)
                except: pass

            time.sleep(10)
        except:
            time.sleep(15)

# --- 6. LANCEMENT ---
if not engine.is_running:
    t = threading.Thread(target=force_loop, daemon=True)
    t.start()
    engine.is_running = True

# --- 7. INTERFACE STREAMLIT ---
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v11.0 Elite")
st.info(f"🌐 État des News : {engine.current_news}")

col1, col2, col3 = st.columns(3)
col1.metric("Moteur", "SMC SNIPER", delta="LIVE")
col2.metric("Scans Effectués", engine.scanned)
col3.metric("Signaux Validés", len(engine.signals))

st.divider()

# Bouton de secours
if engine.scanned == 0:
    st.warning("⚠️ Scan en attente d'initialisation...")
    if st.button("🔴 DÉMARRAGE FORCÉ"):
        fetch_and_analyze("R_10")
        st.rerun()

l, r = st.columns([2, 1])
with l:
    st.subheader("📊 Signaux Sniper (M5 Retest)")
    if not engine.signals: st.info("Le sniper observe le marché... Patientez.")
    for s in reversed(engine.signals[-15:]): st.success(f"🕒 {s['time']} | {s['text']}")
with r:
    st.subheader("📜 Diagnostic Système")
    for log in engine.logs: st.code(log)
    if st.button("🔄 Actualiser"): st.rerun()

time.sleep(20)
st.rerun()
