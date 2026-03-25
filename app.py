import json, requests, threading, time, os, websocket, logging

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MARKETS = ["R_10","R_25","R_50","R_75","R_100",
           "B_300","B_500","B_1000",
           "C_300","C_500","C_1000"]

class Bot:
    def __init__(self):
        self.sent = []

bot = Bot()

# --- TELEGRAM ---
def send_tg(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10
        )
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# --- INDICATEURS ---
def ema(data, period):
    k = 2 / (period + 1)
    ema_val = data[0]
    for price in data:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val

def rsi(closes, period=14):
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- FETCH DATA ---
def get_data(symbol):
    for _ in range(3):  # retry x3
        try:
            ws = websocket.create_connection("wss://ws.binaryws.com/websockets/v3?app_id=1089", timeout=10)

            ws.send(json.dumps({
                "ticks_history": symbol,
                "count": 120,
                "style": "candles",
                "granularity": 300
            }))

            res = json.loads(ws.recv())
            ws.close()

            if 'candles' in res:
                return res['candles']

        except Exception as e:
            logging.warning(f"Retry {symbol}: {e}")
            time.sleep(1)

    return None

# --- STRATEGY ---
def analyze(symbol):
    candles = get_data(symbol)
    if not candles:
        return

    h = [float(x['high']) for x in candles]
    l = [float(x['low']) for x in candles]
    cl = [float(x['close']) for x in candles]

    price = cl[-1]

    # --- SMC ---
    major_h = max(h[20:100])
    major_l = min(l[20:100])

    sweep_sell = h[-2] > major_h and cl[-2] < major_h
    sweep_buy = l[-2] < major_l and cl[-2] > major_l

    last_low = min(l[-12:-2])
    last_high = max(h[-12:-2])

    # --- FILTERS ---
    trend = ema(cl[-50:], 50)
    rsi_val = rsi(cl)

    setup = None

    # SELL
    if sweep_sell and cl[-1] < last_low and price < trend and rsi_val < 50:
        entry = price
        sl = h[-2]
        tp = major_l

        setup = f"🔴 SELL {symbol}\nEntry: {entry}\nSL: {sl}\nTP: {tp}"

    # BUY
    elif sweep_buy and cl[-1] > last_high and price > trend and rsi_val > 50:
        entry = price
        sl = l[-2]
        tp = major_h

        setup = f"🟢 BUY {symbol}\nEntry: {entry}\nSL: {sl}\nTP: {tp}"

    if setup:
        sig = f"{symbol}_{round(price,1)}"

        if sig not in bot.sent:
            bot.sent.append(sig)
            send_tg(setup)

            if len(bot.sent) > 50:
                bot.sent.pop(0)

# --- MAIN LOOP ---
def run():
    logging.info("🚀 BOT RUNNING (RENDER MODE)")

    while True:
        try:
            threads = []

            for s in MARKETS:
                t = threading.Thread(target=analyze, args=(s,))
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            time.sleep(10)

        except Exception as e:
            logging.error(f"Main loop crash: {e}")
            time.sleep(5)

# --- START ---
if __name__ == "__main__":
    run()
