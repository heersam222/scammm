import asyncio
import datetime
import logging
import os

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from telethon import TelegramClient, functions, types as tg_types
from telethon.sessions import StringSession

from dotenv import load_dotenv


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

if not API_ID:
    raise RuntimeError("API_ID is missing")

if not API_HASH:
    raise RuntimeError("API_HASH is missing")

if not SESSION_STRING:
    raise RuntimeError("SESSION_STRING is missing")

API_ID = int(API_ID)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# =========================================================
# BOT + TELETHON USER SESSION
# =========================================================

bot = Bot(token=BOT_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

user_client = TelegramClient(
    StringSession(SESSION_STRING),
    API_ID,
    API_HASH
)


# =========================================================
# ACTIVE ESCROWS
# =========================================================

active_escrows = {}


# =========================================================
# HELPERS
# =========================================================

def display_name(user: types.User) -> str:
    return user.full_name or "Unknown"


def username_text(user: types.User) -> str:
    if user.username:
        return f"@{user.username}"
    return user.full_name or "Unknown"


def get_deal_data(chat_id: int):
    return active_escrows.setdefault(
        chat_id,
        {
            "creator": None,
            "creator_username": None,
            "creator_id": None,

            "buyer": None,
            "buyer_username": None,
            "buyer_id": None,
            "buyer_wallet": None,

            "seller": None,
            "seller_username": None,
            "seller_id": None,
            "seller_wallet": None,

            "token": None,
            "network": None,

            "deal_id": None,
        }
    )


# =========================================================
# START
# =========================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):

    if message.chat.type != "private":
        return

    text = (
        "✨ @PagalEscrowBot ✨\n"
        "Your Trustworthy Telegram Escrow Service\n\n"
        "Welcome to @PagalEscrowBot. This bot provides a reliable escrow "
        "service for your transactions on Telegram.\n"
        "Avoid scams, your funds are safeguarded throughout your deals. "
        "If you run into any issues, simply type /dispute and an arbitrator "
        "will join the group chat within 24 hours.\n\n"
        "🧰 ESCROW FEE:\n"
        "1.0% for P2P and 1.0% for OTC Flat\n\n"
        "🌐 (UPDATES) - (VOUCHES) ✅\n\n"
        "💬 Proceed with /escrow (to start with a new escrow)\n\n"
        "⚠️ IMPORTANT - Make sure coin is same of Buyer and Seller else "
        "you may loose your coin.\n\n"
        "💡 Type /menu to summon a menu with all bots features"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="COMMANDS LIST 🤖",
                    callback_data="cmd_list"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📞 CONTACT",
                    callback_data="contact"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Updates 🔄",
                    callback_data="updates"
                ),
                InlineKeyboardButton(
                    text="Vouches ✅",
                    callback_data="vouches"
                )
            ],
            [
                InlineKeyboardButton(
                    text="WHAT IS ESCROW ?",
                    callback_data="what_is_escrow"
                ),
                InlineKeyboardButton(
                    text="Instructions 👩‍💻",
                    callback_data="instructions"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Terms 📝",
                    callback_data="terms"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Invites 👤",
                    callback_data="invites"
                )
            ],
            [
                InlineKeyboardButton(
                    text="P2P",
                    callback_data="start_p2p"
                ),
                InlineKeyboardButton(
                    text="Product Deal",
                    callback_data="start_product"
                )
            ],
        ]
    )

    await message.answer(
        text,
        reply_markup=keyboard
    )


# =========================================================
# ESCROW CREATION
# =========================================================

@dp.message(Command("escrow"))
async def cmd_escrow(message: types.Message):

    if message.chat.type != "private":
        return

    waiting = await message.answer(
        "Creating a safe trading place for you, please wait..."
    )

    try:

        creator = message.from_user

        # -------------------------------------------------
        # Get bot account through Bot API
        # -------------------------------------------------

        bot_info = await bot.get_me()

        if not bot_info.username:
            raise RuntimeError(
                "Bot must have a username before creating escrow groups."
            )

        # -------------------------------------------------
        # Resolve bot through Telegram USER SESSION
        # -------------------------------------------------

        bot_entity = await user_client.get_entity(
            f"@{bot_info.username}"
        )

        # -------------------------------------------------
        # Create NEW Telegram normal group
        # -------------------------------------------------

        result = await user_client(
            functions.messages.CreateChatRequest(
                users=[bot_entity],
                title="P2P Escrow By PAGAL Bot"
            )
        )

        created_chat = None

        for chat in result.chats:
            if isinstance(chat, tg_types.Chat):
                created_chat = chat
                break

        if created_chat is None:
            raise RuntimeError(
                "Telegram did not return the newly created group."
            )

        chat_id = -abs(created_chat.id)

        # -------------------------------------------------
        # Export invite link
        # -------------------------------------------------

        invite_result = await user_client(
            functions.messages.ExportChatInviteRequest(
                peer=created_chat
            )
        )

        invite_link = getattr(
            invite_result,
            "link",
            None
        )

        if not invite_link:
            raise RuntimeError(
                "Could not create group invite link."
            )

        # -------------------------------------------------
        # Save dynamic creator information
        # -------------------------------------------------

        deal_id = str(creator.id)[-6:]

        active_escrows[chat_id] = {
            "creator": creator.full_name,
            "creator_username": creator.username,
            "creator_id": creator.id,

            "buyer": None,
            "buyer_username": None,
            "buyer_id": None,
            "buyer_wallet": None,

            "seller": None,
            "seller_username": None,
            "seller_id": None,
            "seller_wallet": None,

            "token": None,
            "network": None,

            "deal_id": deal_id,
        }

        # -------------------------------------------------
        # Exact screenshot-style private response
        # -------------------------------------------------

        response_text = (
            "Escrow Group Created\n\n"
            f"Creator: {creator.full_name}\n\n"
            "Join this escrow group and share the link with the buyer "
            "and seller.\n\n"
            f"{invite_link}\n\n"
            "⚠️ Note: This link is for 2 members only—third parties are "
            "not allowed to join."
        )

        await waiting.edit_text(response_text)

        # -------------------------------------------------
        # Send welcome message into newly created group
        # -------------------------------------------------

        welcome_text = (
            "📍 Hey there traders! Welcome to our escrow service.\n"
            "✅ Please start with /dd command and fill the DealInfo Form"
        )

        try:
            sent = await bot.send_message(
                chat_id=chat_id,
                text=welcome_text
            )

            try:
                await bot.pin_chat_message(
                    chat_id=chat_id,
                    message_id=sent.message_id,
                    disable_notification=True
                )
            except Exception as pin_error:
                logger.warning(
                    "Could not pin welcome message: %s",
                    pin_error
                )

        except Exception as bot_group_error:
            logger.exception(
                "Bot could not send welcome message: %s",
                bot_group_error
            )

    except Exception as e:

        logger.exception(
            "ESCROW CREATION FAILED"
        )

        await waiting.edit_text(
            "❌ Error creating group.\n\n"
            f"Details: {str(e)}"
        )


# =========================================================
# /DD
# =========================================================

@dp.message(Command("dd"))
async def cmd_dd(message: types.Message):

    if message.chat.type not in ["group", "supergroup"]:
        return

    text = (
        "Hello there,\n"
        "Kindly tell deal details i.e.\n\n"
        "Quantity -\n"
        "Rate - \n"
        "Conditions (if any) -\n\n"
        "Remember without it disputes wouldn’t be resolved. "
        "Once filled proceed with Specifications of the seller or "
        "buyer with /seller or /buyer [CRYPTO ADDRESS]"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="How To Use Bot ?",
                    callback_data="how_to_use"
                )
            ]
        ]
    )

    await message.answer(
        text,
        reply_markup=keyboard
    )


# =========================================================
# BUYER
# =========================================================

@dp.message(Command("buyer"))
async def cmd_buyer(message: types.Message):

    if message.chat.type not in ["group", "supergroup"]:
        return

    chat_id = message.chat.id
    data = get_deal_data(chat_id)

    user = message.from_user

    args = message.text.split(maxsplit=1)

    wallet = (
        args[1].strip()
        if len(args) > 1
        else "Saved Address"
    )

    data["buyer"] = user.full_name
    data["buyer_username"] = user.username
    data["buyer_id"] = user.id
    data["buyer_wallet"] = wallet

    username = username_text(user)

    text = (
        "📍 ESCROW-ROLE DECLARATION\n\n"
        f"⚡ BUYER {username} | Userid: [{user.id}]\n\n"
        "✅ BUYER WALLET\n"
        f"{wallet}\n\n"
        "Note: If you don't see any address, then your address will "
        "used from saved addresses after selecting token and chain for "
        "the current escrow."
    )

    await message.answer(text)

    await message.answer(
        "Please set seller using /seller [DEPOSIT ADDRESS]"
    )


# =========================================================
# SELLER
# =========================================================

@dp.message(Command("seller"))
async def cmd_seller(message: types.Message):

    if message.chat.type not in ["group", "supergroup"]:
        return

    chat_id = message.chat.id
    data = get_deal_data(chat_id)

    user = message.from_user

    args = message.text.split(maxsplit=1)

    wallet = (
        args[1].strip()
        if len(args) > 1
        else "Saved Address"
    )

    data["seller"] = user.full_name
    data["seller_username"] = user.username
    data["seller_id"] = user.id
    data["seller_wallet"] = wallet

    username = username_text(user)

    text = (
        "📍 ESCROW-ROLE DECLARATION\n\n"
        f"⚡ SELLER {username} | Userid: [{user.id}]\n\n"
        "✅ SELLER WALLET\n"
        f"{wallet}\n\n"
        "Note: If you don't see any address, then your address will "
        "used from saved addresses after selecting token and chain for "
        "the current escrow."
    )

    await message.answer(text)

    await message.answer(
        "Use /token to Choose crypto."
    )


# =========================================================
# TOKEN
# =========================================================

@dp.message(Command("token"))
async def cmd_token(message: types.Message):

    if message.chat.type not in ["group", "supergroup"]:
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="LTC",
                    callback_data="token_LTC"
                ),
                InlineKeyboardButton(
                    text="BTC",
                    callback_data="token_BTC"
                )
            ],
            [
                InlineKeyboardButton(
                    text="USDT",
                    callback_data="token_USDT"
                )
            ],
        ]
    )

    await message.answer(
        "choose token from the list below",
        reply_markup=keyboard
    )


# =========================================================
# TOKEN CALLBACK
# =========================================================

@dp.callback_query(F.data.startswith("token_"))
async def process_token(callback: types.CallbackQuery):

    token = callback.data.split("_", 1)[1]

    chat_id = callback.message.chat.id

    data = get_deal_data(chat_id)

    data["token"] = token

    if token == "USDT":

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="BSC[BEP20]",
                        callback_data="net_BSC"
                    ),
                    InlineKeyboardButton(
                        text="TRON[TRC20]",
                        callback_data="net_TRON"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="Back ⬅️",
                        callback_data="back_token"
                    )
                ],
            ]
        )

        await callback.message.edit_text(
            "📍 ESCROW-CRYPTO DECLARATION\n\n"
            f"✅ CRYPTO\n{token}\n\n"
            "choose network from the list below for USDT",
            reply_markup=keyboard
        )

    else:

        data["network"] = "NATIVE"

        await send_final_declaration(
            callback.message,
            chat_id
        )

    await callback.answer()


# =========================================================
# NETWORK CALLBACK
# =========================================================

@dp.callback_query(F.data.startswith("net_"))
async def process_network(callback: types.CallbackQuery):

    network = callback.data.split("_", 1)[1]

    chat_id = callback.message.chat.id

    data = get_deal_data(chat_id)

    data["network"] = network

    await send_final_declaration(
        callback.message,
        chat_id
    )

    await callback.answer()


# =========================================================
# FINAL DECLARATION
# =========================================================

async def send_final_declaration(
    message: types.Message,
    chat_id: int
):

    data = get_deal_data(chat_id)

    seller = data.get("seller") or "seller"
    seller_id = data.get("seller_id") or "123456"

    buyer = data.get("buyer") or "buyer"
    buyer_id = data.get("buyer_id") or "654321"

    token = data.get("token") or "USDT"
    network = data.get("network") or "BSC"

    seller_username = data.get("seller_username")
    buyer_username = data.get("buyer_username")

    seller_display = (
        f"@{seller_username}"
        if seller_username
        else seller
    )

    buyer_display = (
        f"@{buyer_username}"
        if buyer_username
        else buyer
    )

    text = (
        "📍 ESCROW DECLARATION\n\n"
        f"⚡ Seller {seller_display} | Userid: [{seller_id}]\n"
        f"⚡ Buyer {buyer_display} | Userid: [{buyer_id}]\n\n"
        f"✅ {token} CRYPTO\n"
        f"✅ {network} NETWORK"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Accept ✅",
                    callback_data="accept_deal"
                ),
                InlineKeyboardButton(
                    text="Reject ❌",
                    callback_data="reject_deal"
                ),
            ]
        ]
    )

    await message.edit_text(
        text,
        reply_markup=keyboard
    )


# =========================================================
# ACCEPT
# =========================================================

@dp.callback_query(F.data == "accept_deal")
async def accept_deal(callback: types.CallbackQuery):

    chat_id = callback.message.chat.id

    data = get_deal_data(chat_id)

    deal_id = data.get("deal_id") or "24153438"

    seller = data.get("seller") or "seller"
    seller_id = data.get("seller_id") or "111111"
    seller_wallet = data.get("seller_wallet") or "Saved Address"

    buyer = data.get("buyer") or "buyer"
    buyer_id = data.get("buyer_id") or "222222"
    buyer_wallet = data.get("buyer_wallet") or "Saved Address"

    token = data.get("token") or "USDT"
    network = data.get("network") or "BSC"

    seller_username = data.get("seller_username")
    buyer_username = data.get("buyer_username")

    seller_display = (
        f"@{seller_username}"
        if seller_username
        else seller
    )

    buyer_display = (
        f"@{buyer_username}"
        if buyer_username
        else buyer
    )

    now_str = datetime.datetime.now().strftime(
        "%d/%m/%y %H:%M:%S"
    )

    text = (
        f"📍 TRANSACTION INFORMATION [{deal_id}]\n\n"
        "⚡ SELLER\n"
        f"{seller_display} | [{seller_id}]\n"
        f"{seller_wallet}[{token}]\n"
        f"[{network}]\n\n"
        "⚡ BUYER\n"
        f"{buyer_display} | [{buyer_id}]\n"
        f"{buyer_wallet}[{token}]\n"
        f"[{network}]\n\n"
        f"⏰ Trade Start Time: {now_str}\n\n"
        "⚠️ IMPORTANT: Make sure to finalise and agree each-others "
        "terms before depositing.\n\n"
        "📄 Please use /deposit command to generate a deposit "
        "address for your trade."
    )

    await callback.message.edit_text(text)

    await callback.message.answer(
        "Your Fee is 1.0% as both b
