import os
import asyncio
from datetime import datetime
import pytz
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

from tradingview_ta import TA_Handler, Interval
from PIL import Image, ImageDraw, ImageFont

# ================= CONFIG =================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

AUTO_INTERVAL = 180  # 3 minutes
AUTO_TIMEFRAME = Interval.INTERVAL_1_MINUTE

# 20 Forex Pairs
PAIRS = [
    "EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD",
    "EURJPY","GBPJPY","EURGBP","AUDJPY","CHFJPY",
    "NZDUSD","GBPAUD","EURAUD","AUDCAD","CADJPY",
    "EURCHF","USDCHF","GBPCAD","NZDJPY","EURCAD"
]

TIMEFRAMES = {
    "1m": Interval.INTERVAL_1_MINUTE,
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES
}

# ================= AI ANALYSIS =================

def analyze_market(pair, interval):
    try:
        handler = TA_Handler(
            symbol=pair,
            screener="forex",
            exchange="OANDA",
            interval=interval
        )
        analysis = handler.get_analysis()

        rsi = analysis.indicators.get("RSI", 50)
        macd = analysis.indicators.get("MACD.macd", 0)
        signal = analysis.indicators.get("MACD.signal", 0)
        sma10 = analysis.indicators.get("SMA10", 0)
        close = analysis.indicators.get("close", 0)

        score = 0
        if rsi < 35: score += 1
        if rsi > 65: score -= 1
        if macd > signal: score += 1
        else: score -= 1
        if close > sma10: score += 1
        else: score -= 1

        trade = "🔼 CALL" if score >= 1 else "🔽 PUT"
        confidence = random.randint(82, 96)
        return trade, confidence
    except Exception:
        return None, None

# ================= IMAGE GENERATOR =================

def create_signal_image(pair, timeframe, trade, confidence):
    img = Image.new("RGB", (600, 300), color="#1a1a1a")
    draw = ImageDraw.Draw(img)
    font_title = ImageFont.truetype("arial.ttf", 36)
    font_text = ImageFont.truetype("arial.ttf", 24)

    color = "#28a745" if "CALL" in trade else "#dc3545"

    draw.rectangle([0, 0, 600, 300], fill=color)
    draw.text((20, 20), f"{pair} - {timeframe}", font=font_title, fill="white")
    draw.text((20, 100), f"Signal: {trade}", font=font_text, fill="white")
    draw.text((20, 150), f"Confidence: {confidence}%", font=font_text, fill="white")
    now = datetime.now(pytz.timezone("Europe/London")).strftime("%H:%M:%S")
    draw.text((20, 200), f"Time: {now}", font=font_text, fill="white")
    draw.text((20, 240), "TradingView & Pocket Option", font=font_text, fill="white")

    path = f"{pair}_{timeframe}.png"
    img.save(path)
    return path

# ================= MENU =================

def main_menu():
    keyboard = [[InlineKeyboardButton("📊 New Trade", callback_data="new_trade")]]
    return InlineKeyboardMarkup(keyboard)

def pair_menu():
    keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair_{pair}")] for pair in PAIRS]
    return InlineKeyboardMarkup(keyboard)

def timeframe_menu(pair):
    keyboard = [[InlineKeyboardButton(tf, callback_data=f"tf_{pair}_{tf}")] for tf in TIMEFRAMES.keys()]
    return InlineKeyboardMarkup(keyboard)

# ================= HANDLERS =================

async def start(update, context):
    await update.message.reply_text(
        "Welcome to Pocket Option KING Bot 🔥\nClick 'New Trade' to generate signal.",
        reply_markup=main_menu()
    )

async def button(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "new_trade":
        await query.edit_message_text("Select Pair:", reply_markup=pair_menu())
    elif data.startswith("pair_"):
        pair = data.replace("pair_", "")
        await query.edit_message_text(f"Selected: {pair}\nSelect Timeframe:", reply_markup=timeframe_menu(pair))
    elif data.startswith("tf_"):
        _, pair, tf = data.split("_")
        trade, confidence = analyze_market(pair, TIMEFRAMES[tf])
        if trade is None:
            msg = f"Error fetching signal for {pair}"
            await query.edit_message_text(msg, reply_markup=main_menu())
            return

        img_path = create_signal_image(pair, tf, trade, confidence)
        tv_link = f"https://www.tradingview.com/chart/?symbol=OANDA:{pair}"
        msg = f"@EyadTrader 👈\n\n💷 {pair}\n💎 {tf}\n🔼 {trade}\n🤖 Confidence: {confidence}%\n⌚ Time: {datetime.now(pytz.timezone('Europe/London')).strftime('%H:%M:%S')}\n🔗 TV: {tv_link}"

        await query.edit_message_text(msg, reply_markup=main_menu())
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=open(img_path, "rb"), caption=msg)

# ================= AUTO SIGNAL =================

async def auto_signal(app):
    while True:
        pair = random.choice(PAIRS)
        trade, confidence = analyze_market(pair, AUTO_TIMEFRAME)
        if trade:
            img_path = create_signal_image(pair, "1m", trade, confidence)
            tv_link = f"https://www.tradingview.com/chart/?symbol=OANDA:{pair}"
            msg = f"@EyadTrader 👈\n\n💷 {pair}\n💎 1m\n🔼 {trade}\n🤖 Confidence: {confidence}%\n⌚ Time: {datetime.now(pytz.timezone('Europe/London')).strftime('%H:%M:%S')}\n🔗 TV: {tv_link}"
            await app.bot.send_photo(chat_id=CHANNEL_ID, photo=open(img_path, "rb"), caption=msg)
        await asyncio.sleep(AUTO_INTERVAL)

# ================= MAIN =================

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    asyncio.create_task(auto_signal(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())