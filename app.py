import streamlit as st
import json, requests, threading, time, os, websocket
from datetime import datetime, timedelta
import pytz

# --- 1. CONFIGURATION ---
VERSION = "v11.2 Pro Master"
MAD_TZ = pytz.timezone('Indian/Antananarivo')
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Verrou pour garantir l'unicité du thread de scan
SCAN_THREAD_LOCK = threading.Lock()

# Liste finale des 12 marchés
MARKETS = ["frxXAUUSD", "R_10", "R_25", "R_50", "R_75", "R_100", "B_300", "B_500", "B_1000", "C_300", "C_500", "C_1000"]

st.set_page_config(page_title=f"Mc ANTHONIO VVIP {VERSION}", layout="wide", page_icon="🏛️")

# --- 2. GESTION DE LA MÉMOIRE (ENGINE) ---
class VVIPEngine:
    def __init__(self):
        self.scanned = 0
        self.signals = [] # Stockage détaillé {id, time, text}
        self.logs = []
        self.is_running = False
        self.last_report_hour = -1

    def add_log(self, msg):
        now = datetime.now(MAD_TZ).strftime('%H:%M')
        # Limite à 5 logs pour l'affichage, ajout au début
        self.logs = [f"[{now}] {msg}"] + self.logs[:5]

@st.cache_resource
def get_engine(): return VVIPEngine()
engine = get_engine()

def send_tg(msg):
    if TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            # timeout=8 pour tenir compte des connexions lentes sur mobile
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=8)
        except: pass

# --- 3. LOGIQUE DE NETTOYAGE ---
def cleanup_old_signals():
    """Supprime les signaux datant de plus de 2 heures."""
    if not engine.signals: return

    now = datetime.now(MAD_TZ)
    # Conservation des signaux actifs (< 2h)
    valid_signals = []
    
    for sig in engine.signals:
        if 'time' in sig and (now - sig['time']) < timedelta(hours=2):
            valid_signals.append(sig)
    
    if len(valid_signals) != len(engine.signals):
        diff = len(engine.signals) - len(valid_signals)
        engine.signals = valid_signals
        engine.add_log(f"♻️ Nettoyage: {diff} signal/s obsolète/s supprimé/s")

# --- 4. ANALYSE TECHNIQUE (SMC + DOUBLE TP + FIX SL) ---
def fetch_and_analyze(symbol):
    try:
        ws = websocket.create_connection("wss://ws.binaryws.com/websockets/v3?app_id=1089", timeout=12)
        # CORRECTION : count passé à 300 pour un historique plus riche
        ws.send(json.dumps({"ticks_history": symbol, "count": 300, "style": "candles", "granularity": 300}))
        res = json.loads(ws.recv()); ws.close()

        if 'candles' in res:
            c = res['candles']
            h, l, cl = [float(x['high']) for x in c], [float(x['low']) for x in c], [float(x['close']) for x in c]
            
            # Analyse sur l'historique étendu (détection SMC plus stable)
            # ext_h/l se concentre sur une zone de liquidité externe plus ancienne
            curr_p, ext_h, ext_l = cl[-1], max(h[100:250]), min(l[100:250])

            setup = None
            now_utc = datetime.now(MAD_TZ)

            # Logique BUY (Sweep -> BOS -> Retest)
            rec_l = min(l[-15:])
            if rec_l < ext_l and curr_p > max(h[-12:-2]):
                if curr_p <= ext_l + (abs(ext_l - rec_l) * 0.40):
                    tp2 = ext_h
                    tp1 = curr_p + (abs(tp2 - curr_p) * 0.5)
                    sl = rec_l
                    setup = f"🟢 **BUY SNIPER** {symbol}\n📍 Entrée : `{round(curr_p, 5)}`\n🛡️ **SL :** `{round(sl, 5)}` \n🏆 **TP1 :** `{round(tp1, 5)}` | **TP2 :** `{round(tp2, 5)}`"

            # Logique SELL (Sweep -> BOS -> Retest)
            rec_h = max(h[-15:])
            if rec_h > ext_h and curr_p < min(l[-12:-2]):
                if curr_p >= ext_h - (abs(rec_h - ext_h) * 0.40):
                    tp2 = ext_l
                    tp1 = curr_p - (abs(curr_p - tp2) * 0.5)
                    sl = rec_h
                    setup = f"🔴 **SELL SNIPER** {symbol}\n📍 Entrée : `{round(curr_p, 5)}`\n🛡️ **SL :** `{round(sl, 5)}` \n🏆 **TP1 :** `{round(tp1, 5)}` | **TP2 :** `{round(tp2, 5)}`"

            if setup:
                # Création de l'ID Unique basé sur le symbole et le prix arrondi
                # L'arrondi à .1 permet d'éviter les doublons trop rapprochés
                # exemple: R_10_2345.1
                sig_id = f"{symbol}_{round(curr_p, 1)}" 

                # Vérification de doublon existant (même signal < 2h)
                existing_ids = [s.get('id', '') for s in engine.signals]
                
                if sig_id not in existing_ids:
                    # Enregistrement avec timestamp pour le nettoyage
                    engine.signals.append({"id": sig_id, "time": now_utc, "text": setup})
                    send_tg(f"🏛️ **Mc ANTHONIO VVIP**\n*{VERSION}*\n\n{setup}\n👤 @McAnthonio")
            
            engine.scanned += 1
    except:
        engine.add_log(f"Erreur {symbol}")

# --- 5. BOUCLE DE CONTRÔLE (RAPPORTS & HORAIRES) ---
def core_loop():
    # CORRECTION : Utilisation d'un verrou global pour empêcher la multiplication des threads
    if SCAN_THREAD_LOCK.locked():
        return # Un thread tourne déjà, on n'en crée pas de nouveau
        
    with SCAN_THREAD_LOCK: # Garantit le verrouillage pendant l'exécution
        engine.is_running = True
        engine.add_log(f"🚀 Moteur SMC {VERSION} Démarré")
        
        while True:
            try:
                # Nettoyage systématique à chaque cycle de scan
                cleanup_old_signals()
                
                now = datetime.now(MAD_TZ)
                hr = now.hour

                # Rapports automatiques chaque 3h (9h, 12h, 15h, 18h, 21h)
                if hr in [9, 12, 15, 18, 21] and engine.last_report_hour != hr:
                    cleanup_old_signals() # Nettoyage forcé avant rapport
                    send_tg(f"📊 **RAPPORT VVIP ({hr}h)**\n✅ Scans effectues : {engine.scanned}\n📈 Signaux Valides : {len(engine.signals)}")
                    engine.last_report_hour = hr

                # Plage de scan : 06h00 à 21h00
                if 6 <= hr < 21:
                    for m in MARKETS:
                        fetch_and_analyze(m)
                        time.sleep(5) # Sécurité pour ne pas saturer Render
                    engine.add_log(f"Cycle de scan fini. Total: {engine.scanned}")
                else:
                    if hr == 21 and now.minute < 5:
                        engine.add_log("💤 Mode Veille (Repos 21h)")
                    time.sleep(60) # Mode repos journalier

            except:
                time.sleep(10)

# Lancement sécurisé du thread de scan
if not engine.is_running:
    t = threading.Thread(target=core_loop, daemon=True)
    t.start()

# --- 6. INTERFACE STREAMLIT v11.2 ---
st.title(f"🏛️ Mc ANTHONIO VVIP - {VERSION}")

# Métriques principales avec les infos demandées
col1, col2, col3 = st.columns(3)
col1.metric("Statut Scanner", "06h - 21h", delta="Stable + Nettoyage")
col2.metric("Actifs Surveillés", f"{len(MARKETS)} actifs")
col3.metric("Scans Totaux", engine.scanned)

st.divider()

l, r = st.columns([2, 1])
with l:
    st.subheader("📊 Signaux Sniper (M5 SMC Active)")
    
    # Bouton de nettoyage manuel forcé
    if st.button("♻️ Forcer un nettoyage manuel"):
        cleanup_old_signals()
        st.rerun()
        
    if engine.scanned == 0:
        st.info("⏳ Initialisation du premier cycle (environ 60s)...")
    elif not engine.signals:
        st.info("Recherche active de Sweep & Retest institutionnels (M5)...")
    else:
        # Affiche uniquement les 10 derniers signaux non encore nettoyés
        for s in reversed(engine.signals[-10:]):
            st.success(s['text'])

with r:
    st.subheader("📜 Diagnostic Système")
    st.write(f"Dernier rafraichissement : {datetime.now(MAD_TZ).strftime('%H:%M:%S')}")
    
    # Affichage des logs inversé (plus récent en haut)
    for log in engine.logs:
        st.code(log)
        
    if st.button("🔄 Actualiser l'Interface"):
        st.rerun()

# Auto-refresh de la page toutes les 30 secondes (pour mettre à jour les chronos de nettoyage)
time.sleep(30)
st.rerun()
