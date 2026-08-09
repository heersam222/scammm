import asyncio
import datetime
import logging
import os
import sqlite3
from contextlib import closing

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from dotenv import load_dotenv


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ESCROW_GROUP_ID = int(os.getenv("ESCROW_GROUP_ID", "0"))

CONTACT_USERNAME = os.getenv("CONTACT_USERNAME", "YourContact")
UPDATES_URL = os.getenv("UPDATES_URL", "https://t.me/YourUpdates")
VOUCHES_URL = os.getenv("VOUCHES_URL", "https://t.me/YourVouches")

if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise RuntimeError("BOT_TOKEN is not configured in .env")

if ESCROW_GROUP_ID == 0:
    raise RuntimeError("ESCROW_GROUP_ID is not configured in .env")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("pagal-escrow")


# ============================================================
# BOT
# ============================================================

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ============================================================
# DATABASE
# ============================================================

DB_NAME = "escrow.db"


def init_db():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS escrows (
                chat_id INTEGER PRIMARY KEY,
                creator TEXT,
                creator_id INTEGER,

                buyer TEXT,
                buyer_id INTEGER,
                buyer_wallet TEXT,

                seller TEXT,
                seller_id INTEGER,
                seller_wallet TEXT,

                token TEXT,
                network TEXT,

                deal_id TEXT,
                status TEXT DEFAULT 'created',

                created_at TEXT
            )
            """
        )
        conn.commit()


def save_escrow(chat_id, data):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO escrows (
                chat_id,
                creator,
                creator_id,
                buyer,
                buyer_id,
                buyer_wallet,
                seller,
                seller_id,
                seller_wallet,
                token,
                network,
                deal_id,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                data.get("creator"),
                data.get("creator_id"),
                data.get("buyer"),
                data.get("buyer_id"),
                data.get("buyer_wallet"),
                data.get("seller"),
                data.get("seller_id"),
                data.get("seller_wallet"),
                data.get("token"),
                data.get("network"),
                data.get("deal_id"),
                data.get("status", "created"),
                data.get("created_at"),
            ),
        )
        conn.commit()


def get_escrow(chat_id):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            "SELECT * FROM escrows WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()

        if not row:
            return None

        return dict(row)


def update_escrow(chat_id, **fields):
    if not fields:
        return

    allowed = {
        "creator",
        "creator_id",
        "buyer",
        "buyer_id",
        "buyer_wallet",
        "seller",
        "seller_id",
        "seller_wallet",
        "token",
        "network",
        "deal_id",
        "status",
        "created_at",
    }

    fields = {
        key: value
        for key, value in fields.items()
        if key in allowed
    }

    if not fields:
        return

    set_clause = ", ".join(
        f"{key} = ?" for key in fields
    )

    values = list(fields.values())
    values.append(chat_id)

    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.execute(
            f"""
            UPDATE escrows
            SET {set_clause}
            WHERE chat_id = ?
            """,
            values,
        )
        conn.commit()


init_db()


# ============================================================
# HELPERS
# ============================================================

def now_string():
    return datetime.datetime.now().strftime(
        "%d/%m/%y %H:%M:%S"
    )


def display_user(message: types.Message):
    username = message.from_user.username

    if username:
        return f"@{username}"

    return message.from_user.full_name


def get_or_create_group_escrow(chat_id):
    data = get_escrow(chat_id)

    if data:
        return data

    data = {
        "creator": None,
        "creator_id": None,
        "buyer": None,
        "buyer_id": None,
        "buyer_wallet": None,
        "seller": None,
        "seller_id": None,
        "seller_wallet": None,
        "token": None,
        "network": None,
        "deal_id": str(abs(chat_id))[-8:],
        "status": "created",
        "created_at": now_string(),
    }

    save_escrow(chat_id, data)

    return data


async def is_admin(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return False

    member = await bot.get_chat_member(
        message.chat.id,
        message.from_user.id,
    )

    return member.status in ("administrator", "creator")


async def send_final_declaration(
    message: types.Message,
    chat_id: int,
):
    data = get_escrow(chat_id) or {}

    seller = data.get("seller") or "seller"
    seller_id = data.get("seller_id") or "123456"

    buyer = data.get("buyer") or "buyer"
    buyer_id = data.get("buyer_id") or "654321"

    token = data.get("token") or "USDT"
    network = data.get("network") or "BSC"

    text = (
        "📍 ESCROW DECLARATION\n\n"
        f"⚡ Seller {seller} | Userid: [{seller_id}]\n"
        f"⚡ Buyer {buyer} | Userid: [{buyer_id}]\n\n"
        f"✅ {token} CRYPTO\n"
        f"✅ {network} NETWORK"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Accept ✅",
                    callback_data="accept_deal",
                ),
                InlineKeyboardButton(
                    text="Reject ❌",
                    callback_data="reject_deal",
                ),
            ]
        ]
    )

    await message.edit_text(
        text,
        reply_markup=keyboard,
    )


# ============================================================
# /START
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):

    if message.chat.type != "private":
        return

    text = (
        "✨ @PagalEscrowBot ✨\n"
        "Your Trustworthy Telegram Escrow Service\n\n"
        "Welcome to @PagalEscrowBot. This bot provides a reliable "
        "escrow service for your transactions on Telegram.\n"
        "Avoid scams, your funds are safeguarded throughout your deals. "
        "If you run into any issues, simply type /dispute and an "
        "arbitrator will join the group chat within 24 hours.\n\n"
        "🧰 ESCROW FEE:\n"
        "1.0% for P2P and 1.0% for OTC Flat\n\n"
        "🌐 (UPDATES) - (VOUCHES) ✅\n\n"
        "💬 Proceed with /escrow (to start with a new escrow)\n\n"
        "⚠️ IMPORTANT - Make sure coin is same of Buyer and Seller "
        "else you may loose your coin.\n\n"
        "💡 Type /menu to summon a menu with all bots features"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="COMMANDS LIST 🤖",
                    callback_data="cmd_list",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📞 CONTACT",
                    callback_data="contact",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Updates 🔄",
                    url=UPDATES_URL,
                ),
                InlineKeyboardButton(
                    text="Vouches ✅",
                    url=VOUCHES_URL,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="WHAT IS ESCROW ?",
                    callback_data="what_is_escrow",
                ),
                InlineKeyboardButton(
                    text="Instructions 👩‍💻",
                    callback_data="instructions",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Terms 📝",
                    callback_data="terms",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Invites 👤",
                    callback_data="invites",
                )
            ],
            [
                InlineKeyboardButton(
                    text="P2P",
                    callback_data="start_p2p",
                ),
                InlineKeyboardButton(
                    text="Product Deal",
                    callback_data="start_product",
                ),
            ],
        ]
    )

    await message.answer(
        text,
        reply_markup=keyboard,
    )


# ============================================================
# /MENU
# ============================================================

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):

    if message.chat.type != "private":
        return

    await cmd_start(message)


# ============================================================
# /ESCROW
# ============================================================

@dp.message(Command("escrow"))
async def cmd_escrow(message: types.Message):

    if message.chat.type != "private":
        return

    msg = await message.answer(
        "Creating a safe trading place for you, please wait..."
    )

    try:

        # Telegram Bot API cannot create a new group.
        # Therefore we create a unique invite link in the configured
        # escrow supergroup.

        invite = await bot.create_chat_invite_link(
            chat_id=ESCROW_GROUP_ID,
            name=f"Escrow {message.from_user.id}",
            member_limit=2,
        )

        deal_id = str(message.from_user.id)[-8:]

        data = {
            "creator": message.from_user.full_name,
            "creator_id": message.from_user.id,

            "buyer": None,
            "buyer_id": None,
            "buyer_wallet": None,

            "seller": None,
            "seller_id": None,
            "seller_wallet": None,

            "token": None,
            "network": None,

            "deal_id": deal_id,
            "status": "created",
            "created_at": now_string(),
        }

        # We can't know the new chat ID before the user joins,
        # so the deal ID is included in the invite name.
        # Group initialization happens when /dd is used.

        response_text = (
            "Escrow Group Created\n\n"
            f"Creator: {message.from_user.full_name}\n\n"
            "Join this escrow group and share the link with the "
            "buyer and seller.\n\n"
            f"{invite.invite_link}\n\n"
            "⚠️ Note: This link is for 2 members only—third parties "
            "are not allowed to join."
        )

        await msg.edit_text(response_text)

    except Exception as e:

        logger.exception("Escrow invite error")

        await msg.edit_text(
            "❌ Error creating escrow invite.\n\n"
            "Make sure the bot is an administrator in the configured "
            "escrow supergroup and has permission to invite users.\n\n"
            f"Details: {str(e)}"
        )


# ============================================================
# GROUP /DD
# ============================================================

@dp.message(Command("dd"))
async def cmd_dd(message: types.Message):

    if message.chat.type not in ("group", "supergroup"):
        return

    get_or_create_group_escrow(message.chat.id)

    text = (
        "Hey there traders! Welcome to our escrow service.\n\n"
        "📌 Kindly tell deal details i.e.\n\n"
        "Quantity -\n"
        "Rate -\n"
        "Conditions (if any) -\n\n"
        "Remember without it disputes wouldn’t be resolved. "
        "Once filled proceed with Specifications of the seller "
        "or buyer with /seller or /buyer [CRYPTO ADDRESS]"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="How To Use Bot ?",
                    callback_data="how_to_use",
                )
            ]
        ]
    )

    await message.answer(
        text,
        reply_markup=keyboard,
    )


# ============================================================
# /BUYER
# ============================================================

@dp.message(Command("buyer"))
async def cmd_buyer(message: types.Message):

    if message.chat.type not in ("group", "supergroup"):
        return

    data = get_or_create_group_escrow(message.chat.id)

    args = message.text.split(maxsplit=1)

    wallet = (
        args[1].strip()
        if len(args) > 1
        else "Saved Address"
    )

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else message.from_user.full_name
    )

    user_id = message.from_user.id

    update_escrow(
        message.chat.id,
        buyer=username,
        buyer_id=user_id,
        buyer_wallet=wallet,
    )

    text = (
        "📍 ESCROW-ROLE DECLARATION\n\n"
        f"⚡ BUYER {username} | Userid: [{user_id}]\n\n"
        "✅ BUYER WALLET\n"
        f"{wallet}\n\n"
        "Note: If you don't see any address, then your address "
        "will used from saved addresses after selecting token "
        "and chain for the current escrow."
    )

    await message.answer(text)

    await message.answer(
        "Please set seller using /seller [DEPOSIT ADDRESS]"
    )


# ============================================================
# /SELLER
# ============================================================

@dp.message(Command("seller"))
async def cmd_seller(message: types.Message):

    if message.chat.type not in ("group", "supergroup"):
        return

    get_or_create_group_escrow(message.chat.id)

    args = message.text.split(maxsplit=1)

    wallet = (
        args[1].strip()
        if len(args) > 1
        else "Saved Address"
    )

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else message.from_user.full_name
    )

    user_id = message.from_user.id

    update_escrow(
        message.chat.id,
        seller=username,
        seller_id=user_id,
        seller_wallet=wallet,
    )

    text = (
        "📍 ESCROW-ROLE DECLARATION\n\n"
        f"⚡ SELLER {username} | Userid: [{user_id}]\n\n"
        "✅ SELLER WALLET\n"
        f"{wallet}\n\n"
        "Note: If you don't see any address, then your address "
        "will used from saved addresses after selecting token "
        "and chain for the current escrow."
    )

    await message.answer(text)

    await message.answer(
        "Use /token to Choose crypto."
    )


# ============================================================
# /TOKEN
# ============================================================

@dp.message(Command("token"))
async def cmd_token(message: types.Message):

    if message.chat.type not in ("group", "supergroup"):
        return

    get_or_create_group_escrow(message.chat.id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="LTC",
                    callback_data="token_LTC",
                ),
                InlineKeyboardButton(
                    text="BTC",
                    callback_data="token_BTC",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="USDT",
                    callback_data="token_USDT",
                )
            ],
        ]
    )

    await message.answer(
        "choose token from the list below",
        reply_markup=keyboard,
    )


# ============================================================
# TOKEN CALLBACK
# ============================================================

@dp.callback_query(F.data.startswith("token_"))
async def process_token(
    callback: types.CallbackQuery,
):

    token = callback.data.split("_", 1)[1]

    chat_id = callback.message.chat.id

    get_or_create_group_escrow(chat_id)

    update_escrow(
        chat_id,
        token=token,
    )

    if token == "USDT":

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="BSC[BEP20]",
                        callback_data="net_BSC",
                    ),
                    InlineKeyboardButton(
                        text="TRON[TRC20]",
                        callback_data="net_TRON",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="Back ⬅️",
                        callback_data="back_token",
                    )
                ],
            ]
        )

        await callback.message.edit_text(
            "📍 ESCROW-CRYPTO DECLARATION\n\n"
            f"✅ CRYPTO\n{token}\n\n"
            "choose network from the list below for USDT",
            reply_markup=keyboard,
        )

    else:

        update_escrow(
            chat_id,
            network="NATIVE",
        )

        await send_final_declaration(
            callback.message,
            chat_id,
        )

    await callback.answer()


# ============================================================
# NETWORK CALLBACK
# ============================================================

@dp.callback_query(F.data.startswith("net_"))
async def process_network(
    callback: types.CallbackQuery,
):

    network = callback.data.split("_", 1)[1]

    chat_id = callback.message.chat.id

    get_or_create_group_escrow(chat_id)

    update_escrow(
        chat_id,
        network=network,
    )

    await send_final_declaration(
        callback.message,
        chat_id,
    )

    await callback.answer()


# ============================================================
# BACK TOKEN
# ============================================================

@dp.callback_query(F.data == "back_token")
async def back_token(
    callback: types.CallbackQuery,
):

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="LTC",
                    callback_data="token_LTC",
                ),
                InlineKeyboardButton(
                    text="BTC",
                    callback_data="token_BTC",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="USDT",
                    callback_data="token_USDT",
                )
            ],
        ]
    )

    await callback.message.edit_
