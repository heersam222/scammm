
import os
import logging
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ============================================================
# OWN / DEMO P2P ESCROW BOT
# ------------------------------------------------------------
# This version reproduces the Telegram UI/message flow shown
# in the screenshots, but does NOT custody, transfer, release,
# refund, or verify real cryptocurrency.
#
# Railway variables:
#   BOT_TOKEN       = Telegram bot token
#   BOT_USERNAME    = Bot username WITHOUT @
#   BRAND_NAME      = Your bot/group brand
#   FEE_PERCENT     = e.g. 1.0
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourEscrowBot").strip().lstrip("@")
BRAND_NAME = os.getenv("BRAND_NAME", "MY ESCROW BOT").strip()
FEE_PERCENT = os.getenv("FEE_PERCENT", "1.0").strip()

# In-memory trade state. For production, use a real database.
trades = {}


def user_name(user):
    if user.username:
        return f"@{user.username}"
    return user.full_name or "User"


def uid(user):
    return user.id


def get_trade(chat_id):
    return trades.setdefault(
        chat_id,
        {
            "seller": None,
            "buyer": None,
            "seller_wallet": None,
            "token": None,
            "network": None,
            "accepted": False,
            "tx_id": None,
            "created": None,
        },
    )


def transaction_id(chat_id):
    trade = get_trade(chat_id)
    if not trade["tx_id"]:
        # Demo transaction reference only.
        trade["tx_id"] = str(abs(hash(f"{chat_id}-{datetime.now().isoformat()}")))[:8]
    return trade["tx_id"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"📌 {BRAND_NAME}\n\n"
        "Welcome to our P2P escrow bot.\n\n"
        "Available commands:\n"
        "/seller <wallet> — set seller\n"
        "/token — choose crypto\n"
        "/deposit — create a demo deposit session\n"
        "/status — view current trade\n\n"
        "⚠️ Demo mode: no real cryptocurrency is transferred or held."
    )
    await update.message.reply_text(text)


async def seller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    trade = get_trade(update.effective_chat.id)
    user = update.effective_user

    wallet = " ".join(context.args).strip() if context.args else ""

    if wallet:
        trade["seller_wallet"] = wallet

    trade["seller"] = {
        "name": user_name(user),
        "id": uid(user),
    }

    wallet_text = trade["seller_wallet"] or "Not provided"

    text = (
        f"📌 ESCROW-ROLE DECLARATION\n\n"
        f"⚡ SELLER {user_name(user)} | Userid: [{uid(user)}]\n\n"
        f"✅ SELLER WALLET\n"
        f"{wallet_text}\n\n"
        "Note: If you don't see any address, then your address will "
        "used from saved addresses after selecting token and chain "
        "for the current escrow."
    )

    await update.message.reply_text(text)

    await update.message.reply_text(
        "Use /token to Choose crypto."
    )


async def token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    trade = get_trade(update.effective_chat.id)

    # Default display follows the screenshots.
    trade["token"] = "USDT"
    trade["network"] = "BSC"

    keyboard = [
        [
            InlineKeyboardButton("Accept ✅", callback_data="accept_token"),
            InlineKeyboardButton("Reject ❌", callback_data="reject_token"),
        ]
    ]

    text = (
        "📌 ESCROW DECLARATION\n\n"
        f"⚡ Seller {trade['seller']['name'] if trade['seller'] else 'Not set'}"
        f" | Userid: [{trade['seller']['id'] if trade['seller'] else 'N/A'}]\n\n"
        "✅ USDT CRYPTO\n"
        "✅ BSC NETWORK"
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    trade = get_trade(chat_id)

    if query.data == "reject_token":
        await query.edit_message_text(
            "❌ Crypto selection rejected.\nUse /token to choose again."
        )
        return

    if query.data == "accept_token":
        trade["accepted"] = True

        if not trade["buyer"]:
            trade["buyer"] = {
                "name": user_name(query.from_user),
                "id": uid(query.from_user),
            }

        text = (
            "📌 ESCROW DECLARATION\n\n"
            f"⚡ Buyer {trade['buyer']['name']} | Userid: [{trade['buyer']['id']}]\n"
            f"⚡ Seller {trade['seller']['name'] if trade['seller'] else 'N/A'}"
            f" | Userid: [{trade['seller']['id'] if trade['seller'] else 'N/A'}]\n\n"
            "✅ USDT CRYPTO\n"
            "✅ BSC NETWORK"
        )

        await query.edit_message_text(text)

        await query.message.reply_text(
            f"📌 TRANSACTION INFORMATION [{transaction_id(chat_id)}]\n\n"
            f"⚡ SELLER\n"
            f"{trade['seller']['name'] if trade['seller'] else 'N/A'}"
            f" | [{trade['seller']['id'] if trade['seller'] else 'N/A'}]\n"
            f"{trade['seller_wallet'] or 'Not provided'} [USDT]\n"
            "[BSC]\n\n"
            f"⚡ BUYER\n"
            f"{trade['buyer']['name']} | [{trade['buyer']['id']}]\n\n"
            f"⏰ Trade Start Time: "
            f"{datetime.now().strftime('%d/%m/%y %H:%M:%S')}\n\n"
            "⚠️ IMPORTANT: Make sure to finalise and agree each-other "
            "terms before depositing.\n\n"
            "📄 Please use /deposit command to generate a demo deposit "
            "session for your trade."
        )


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    trade = get_trade(chat_id)

    if not trade["accepted"]:
        await update.message.reply_text(
            "⚠️ Please complete /token and Accept the crypto selection first."
        )
        return

    # Deliberately NOT a real blockchain deposit address.
    demo_address = "DEMO-DEPOSIT-ADDRESS-NOT-A-CRYPTO-WALLET"

    keyboard = [
        [InlineKeyboardButton("Check Payment", callback_data="check_payment")]
    ]

    await update.message.reply_text(
        "Requesting a deposit address for you, please wait..."
    )

    text = (
        f"📌 TRANSACTION INFORMATION [{transaction_id(chat_id)}]\n\n"
        f"⚡ SELLER\n"
        f"{trade['seller']['name'] if trade['seller'] else 'N/A'}"
        f" | [{trade['seller']['id'] if trade['seller'] else 'N/A'}]\n\n"
        f"⚡ BUYER\n"
        f"{trade['buyer']['name'] if trade['buyer'] else 'N/A'}"
        f" | [{trade['buyer']['id'] if trade['buyer'] else 'N/A'}]\n\n"
        f"🟢 DEMO ESCROW SESSION\n"
        f"{demo_address}\n"
        "[USDT]\n[BSC]\n\n"
        f"Seller [{trade['seller']['name'] if trade['seller'] else 'N/A'}] "
        "will use this demo session for the trade.\n\n"
        "Amount Received: 0.00000 [0.00$]\n\n"
        f"⏰ Trade Start Time: "
        f"{datetime.now().strftime('%d/%m/%y %H:%M:%S')}\n"
        "⏰ Demo Session: 20.00 Min\n\n"
        "📄 Note: This is a demonstration only. No real crypto is "
        "accepted, held, released, or refunded by this bot.\n\n"
        "Useful commands:\n"
        "📄 /release = Demo release flow only.\n"
        "📄 /refund = Demo refund flow only."
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    await update.message.reply_text(
        f"Your Fee is {FEE_PERCENT}% as both buyer and seller are "
        f"not using @{BOT_USERNAME} in your bio."
    )


async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "🔎 Payment check\n\n"
        "Amount Received: 0.00000 [0.00$]\n\n"
        "⚠️ Demo mode: this bot does not connect to a blockchain "
        "and cannot confirm real payments."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    trade = get_trade(update.effective_chat.id)

    await update.message.reply_text(
        "📊 TRADE STATUS\n\n"
        f"Seller: {trade['seller']['name'] if trade['seller'] else 'Not set'}\n"
        f"Buyer: {trade['buyer']['name'] if trade['buyer'] else 'Not set'}\n"
        f"Crypto: {trade['token'] or 'Not selected'}\n"
        f"Network: {trade['network'] or 'Not selected'}\n"
        f"Accepted: {'Yes' if trade['accepted'] else 'No'}\n"
        f"Transaction ID: {trade['tx_id'] or 'Not created'}\n\n"
        "⚠️ Demo mode."
    )


async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📤 DEMO RELEASE\n\n"
        "The release flow was triggered, but no real funds are transferred.\n"
        "For real-money custody/release, use a properly audited "
        "non-custodial or regulated payment architecture."
    )


async def refund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "↩️ DEMO REFUND\n\n"
        "The refund flow was triggered, but no real funds are transferred."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n\n"
        "/start\n"
        "/seller <wallet>\n"
        "/token\n"
        "/deposit\n"
        "/status\n"
        "/release\n"
        "/refund"
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is missing. "
            "Add your Telegram bot token in Railway Variables."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("seller", seller))
    app.add_handler(CommandHandler("token", token))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("release", release))
    app.add_handler(CommandHandler("refund", refund))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button, pattern="^(accept_token|reject_token)$"))
    app.add_handler(CallbackQueryHandler(check_payment, pattern="^check_payment$"))

    log.info("%s started", BRAND_NAME)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
