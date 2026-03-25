import streamlit as st
import json, requests, threading, time, os, websocket
from datetime import datetime, timedelta
import pytz

# --- CONFIGURATION DES ACCÈS ---
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FINNHUB_KEY = os.getenv("FINNHUB_TOKEN")
APP_URL = os.getenv("APP_URL") # Ton URL Render (ex: https://mon-bot.onrender.com)

MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

st.set_page_config(page_title="Mc ANTHONIO VVIP v11.0 Elite", layout="wide", page_icon="🏛️")

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

# --- SYSTÈME ANTI-SOMMEIL (SELF-PING) ---
def keep_alive():
    while True:
        if APP_URL:
            try: requests.get(APP_URL, timeout=10)
            except: pass
        time.sleep(600) # Ping toutes les 10 minutes

# --- ANALYSE DES NEWS (FINNHUB) ---
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
        if not found: engine.current_news = "Standard (Pas de news majeure)"
    except: engine.current_news = "Erreur News API"

def send_tg(msg):
    if TOKEN and CHAT_ID:
        try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                           json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
        except: pass

# --- ANALYSE SMC : SWEEP -> BOS -> RETEST ---
def fetch_and_analyze(symbol):
    try:
        ws = websocket.create_connection("wss://ws.binaryws.com/websockets/v3?app_id=1089", timeout=10)
        ws.send(json.dumps({"ticks_history": symbol, "count": 100, "style": "candles", "granularity": 300}))
        res = json.loads(ws.recv()); ws.close()

        if 'candles' in res:
            c = res['candles']
            h, l, cl = [float(x['high']) for x in c], [float(x['low']) for x in c], [float(x['close']) for x in c]
            curr_p = cl[-1]
            ext_h, ext_l = max(h[20:80]), min(l[20:80]) # Liquidité externe

            setup = None
            # LOGIQUE BUY : SWEEP BAS -> BOS -> RETEST ZONE SWEEP
            rec_l = min(l[-15:])
            if rec_l < ext_l: # Sweep
                if curr_p > max(h[-12:-2]): # BOS
                    if curr_p <= ext_l + (abs(ext_l - rec_l) * 0.40): # Retest zone sweep
                        setup = f"🟢 **BUY SNIPER** {symbol}\n🎯 Mitigation Zone ✅\n📍 Entrée : `{curr_p}`\n🛡️ SL : `{round(rec_l, 2)}` | 🏆 TP : `{round(ext_h, 2)}`"

            # LOGIQUE SELL : SWEEP HAUT -> BOS -> RETEST ZONE SWEEP
            rec_h = max(h[-15:])
            if rec_h > ext_h: # Sweep
                if curr_p < min(l[-12:-2]): # BOS
                    if curr_p >= ext_h - (abs(rec_h - ext_h) * 0.40): # Retest zone sweep
                        setup = f"🔴 **SELL SNIPER** {symbol}\n🎯 Mitigation Zone ✅\n📍 Entrée : `{curr_p}`\n🛡️ SL : `{round(rec_h, 2)}` | 🏆 TP : `{round(ext_l, 2)}`"

            if setup:
                sig_id = f"{symbol}_{round(curr_p, 2)}"
                if sig_id not in [s.get('id', '') for s in engine.signals]:
                    engine.signals.append({"id": sig_id, "text": setup, "time": datetime.now(MAD_TZ).strftime('%H:%M')})
                    send_tg(f"🏛️ **Mc ANTHONIO VVIP**\n\n{setup}\n🌐 News : {engine.current_news}\n👤 @McAnthonio")
            engine.scanned += 1
    except: pass

# --- BOUCLE DE CONTRÔLE 24/7 ---
def force_loop():
    while True:
        now = datetime.now(MAD_TZ)
        hr, dy, dt = now.hour, now.weekday(), now.strftime("%Y-%m-%d")

        # 1. Check News toutes les 30 min
        if now.minute % 30 == 0: check_news()

        # 2. Ouverture & Motivation (06:00)
        if hr == 6 and engine.last_motivation_day != dt:
            send_tg("☀️ **SESSION OUVERTE - Mc ANTHONIO VVIP**\n\n🔥 *Discipline :* Le prix doit revenir tester la zone de liquidité (Retest).\n🚀 Sois patient, le marché te paiera pour ton attente.")
            engine.last_motivation_day = dt

        # 3. Rapports (9h, 12h, 15h, 18h, 21h)
        if hr in [9, 12, 15, 18, 21] and engine.last_report_hour != hr:
            send_tg(f"📊 **RAPPORT VVIP ({hr}h)**\n✅ Scans : {engine.scanned}\n📈 Signaux : {len(engine.signals)}\n🌐 News : {engine.current_news}")
            engine.last_report_hour = hr

        # 4. Scan Actif (06:00 - 22:00)
        if 6 <= hr < 22:
            for m in MARKETS:
                if m == "frxXAUUSD" and dy >= 5: continue
                fetch_and_analyze(m)
                time.sleep(1.5)
        else:
            if hr == 22: engine.add_log("💤 Mise en veille (22h)")
            time.sleep(60)
        time.sleep(5)

if not engine.is_running:
    threading.Thread(target=force_loop, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start() # Anti-sommeil
    engine.is_running = True

# --- INTERFACE ---
st.title("🏛️ Mc ANTHONIO VVIP - Terminal v11.0 Elite")
st.info(f"🌐 État des News : {engine.current_news}")

c1, c2, c3 = st.columns(3)
c1.metric("Moteur", "SMC MITIGATION", delta="ACTIF")
c2.metric("Scans", engine.scanned)
c3.metric("Signaux", len(engine.signals))

st.divider()
l, r = st.columns([2, 1])
with l:
    st.subheader("📊 Flux Sniper (Sweep Retest)")
    if not engine.signals: st.info("Le sniper observe... Attente d'un retour en zone de liquidité.")
    for s in reversed(engine.signals[-15:]): st.success(f"🕒 {s['time']} | {s['text']}")
with r:
    st.subheader("📜 Diagnostic")
    for log in engine.logs: st.code(log)
    if st.button("🔄 Actualiser"): st.rerun()

time.sleep(15)
st.rerun()
