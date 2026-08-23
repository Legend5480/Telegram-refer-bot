import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Configuration ---
BOT_TOKEN = "8823007340:AAEJ_NJ38Jsn2YACfI7jjBJtRSoZJxvbwUE"
CHANNEL_ID = "@Legend_Giveways"
CHANNEL_LINK = "https://t.me/Legend_Giveways"
REFERRAL_POINTS = 10

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- SQLite Database Functions ---
def init_db():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            referred_by TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, balance, referrals, referred_by FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def add_user(user_id, referred_by=None):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, balance, referrals, referred_by) VALUES (?, 0, 0, ?)", (user_id, referred_by))
    conn.commit()
    conn.close()

def update_referral(referrer_id, new_user_id):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ?, referrals = referrals + 1 WHERE user_id = ?", (REFERRAL_POINTS, referrer_id))
    cursor.execute("UPDATE users SET referred_by = 'DONE' WHERE user_id = ?", (new_user_id,))
    conn.commit()
    conn.close()

# --- Helpers ---
async def is_user_joined(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

def get_force_join_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Joined / Check", callback_data="check_join")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="balance"), InlineKeyboardButton("🔗 Refer Link", callback_data="refer")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    existing_user = get_user(user_id)
    if not existing_user:
        referred_by = None
        if context.args and context.args[0].isdigit():
            ref_id = int(context.args[0])
            if ref_id != user_id:
                referred_by = str(ref_id)
        add_user(user_id, referred_by)

    joined = await is_user_joined(user_id, context)
    if not joined:
        await update.message.reply_text(
            "⚠️ Bot use karne ke liye pehle hamara channel join karein!",
            reply_markup=get_force_join_keyboard()
        )
        return

    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\nAap bot use kar sakte hain.",
        reply_markup=get_main_menu()
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "check_join":
        joined = await is_user_joined(user_id, context)
        if joined:
            user_data = get_user(user_id)
            if user_data and user_data[3] and user_data[3] != "DONE":
                referrer_id = int(user_data[3])
                update_referral(referrer_id, user_id)
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 Naya referral juda! Aapko {REFERRAL_POINTS} points mile."
                    )
                except Exception:
                    pass

            await query.edit_message_text(
                "✅ Thank you join karne ke liye! Main Menu:",
                reply_markup=get_main_menu()
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Aapne abhi tak channel join nahi kiya hai. Pehle join karein!"
            )

    elif query.data == "balance":
        user_data = get_user(user_id)
        balance = user_data[1] if user_data else 0
        referrals = user_data[2] if user_data else 0
        await query.message.reply_text(
            f"💰 *Aapka Balance:*\nPoints: {balance}\nTotal Referrals: {referrals}",
            parse_mode="Markdown"
        )

    elif query.data == "refer":
        bot_username = (await context.bot.get_me()).username
        refer_link = f"https://t.me/{bot_username}?start={user_id}"
        await query.message.reply_text(
            f"🔗 *Aapka Referral Link:*\n`{refer_link}`\n\nPer Refer: {REFERRAL_POINTS} Points",
            parse_mode="Markdown"
        )

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    print("Bot is running with SQLite DB...")
    app.run_polling()

if __name__ == "__main__":
    main()
  
