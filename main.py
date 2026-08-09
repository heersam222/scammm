import asyncio
import datetime
import logging
import os

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ESCROW_GROUP_ID = os.getenv("ESCROW_GROUP_ID", "")

if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise RuntimeError("BOT_TOKEN is missing")

if not ESCROW_GROUP_ID:
    raise RuntimeError("ESCROW_GROUP_ID is missing")

try:
    ESCROW_GROUP_ID = int(ESCROW_GROUP_ID)
except ValueError:
    raise RuntimeError("ESCROW_GROUP_ID must be a number")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# BOT
# ============================================================

bot = Bot(token=TOKEN)

storage = MemoryStorage()

dp = Dispatcher(storage=storage)


# ============================================================
# ACTIVE ESCROWS
# ============================================================

active_escrows = {}


# ============================================================
# HELPERS
# ============================================================

def get_escrow(chat_id: int):

    if chat_id not in active_escrows:

        active_escrows[chat_id] = {
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

            "deal_id": None,
            "status": "created",
        }

    return active_escrows[chat_id]


def now_string():

    return datetime.datetime.now().strftime(
        "%d/%m/%y %H:%M:%S"
    )


# ============================================================
# START & MENU COMMANDS
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
                ),
            ],

            [
                InlineKeyboardButton(
                    text="WHAT IS ESCROW ?",
                    callback_data="what_is_escrow"
                ),

                InlineKeyboardButton(
                    text="Instructions 👩‍💻",
                    callback_data="instructions"
                ),
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
                ),
            ],
        ]
    )

    await message.answer(
        text,
        reply_markup=keyboard
    )


# ============================================================
# MENU
# ============================================================

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):

    if message.chat.type != "private":
        return

    await cmd_start(message)


# ============================================================
# ESCROW
# ============================================================

@dp.message(Command("escrow"))
async def cmd_escrow(message: types.Message):

    if message.chat.type != "private":
        return

    msg = await message.answer(
        "Creating a safe trading place for you, please wait..."
    )

    await asyncio.sleep(1)

    try:

        deal_id = str(message.from_user.id)[-6:]

        invite = await bot.create_chat_invite_link(
            chat_id=ESCROW_GROUP_ID,
            name=f"Escrow-{deal_id}",
            member_limit=2
        )

        active_escrows[ESCROW_GROUP_ID] = {
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
        }

        response_text = (
            "Escrow Group Created\n\n"
            f"Creator: {message.from_user.full_name}\n\n"
            "Join this escrow group and share the link with the buyer and "
            "seller.\n\n"
            f"{invite.invite_link}\n\n"
            "⚠️ Note: This link is for 2 members only—third parties are "
            "not allowed to join."
        )

        await msg.edit_text(response_text)

    except Exception as e:

        logger.exception("ESCROW ERROR")

        await msg.edit_text(
            "❌ Error creating group. Make sure the bot has rights or add it"
            f" properly. Details: {str(e)}"
        )


# ============================================================
# GROUP ACTIONS & /dd COMMAND
# ============================================================

@dp.message(Command("dd"))
async def cmd_dd(message: types.Message):

    if message.chat.type in ["group", "supergroup"]:

        get_escrow(message.chat.id)

        text = (
            "Hello there,\nKindly tell deal details i.e.\n\nQuantity -\nRate -"
            " \nConditions (if any) -\n\nRemember without it disputes wouldn’t be"
            " resolved. Once filled proceed with Specifications of the seller or"
            " buyer with /seller or /buyer [CRYPTO ADDRESS]"
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


# ============================================================
# BUYER
# ============================================================

@dp.message(Command("buyer"))
async def cmd_buyer(message: types.Message):

    if message.chat.type in ["group", "supergroup"]:

        data = get_escrow(message.chat.id)

        args = message.text.split(maxsplit=1)

        wallet = (
            args[1]
            if len(args) > 1
            else "Saved Address"
        )

        username = (
            message.from_user.username
            or message.from_user.full_name
        )

        user_id = message.from_user.id

        data["buyer"] = username
        data["buyer_id"] = user_id
        data["buyer_wallet"] = wallet

        text = (
            f"📍 ESCROW-ROLE DECLARATION\n\n⚡ BUYER @{username} | Userid:"
            f" [{user_id}]\n\n✅ BUYER WALLET\n{wallet}\n\nNote: If you don't see"
            " any address, then your address will used from saved addresses after"
            " selecting token and chain for the current escrow."
        )

        await message.answer(text)

        await message.answer(
            "Please set seller using /seller [DEPOSIT ADDRESS]"
        )


# ============================================================
# SELLER
# ============================================================

@dp.message(Command("seller"))
async def cmd_seller(message: types.Message):

    if message.chat.type in ["group", "supergroup"]:

        data = get_escrow(message.chat.id)

        args = message.text.split(maxsplit=1)

        wallet = (
            args[1]
            if len(args) > 1
            else "Saved Address"
        )

        username = (
            message.from_user.username
            or message.from_user.full_name
        )

        user_id = message.from_user.id

        data["seller"] = username
        data["seller_id"] = user_id
        data["seller_wallet"] = wallet

        text = (
            f"📍 ESCROW-ROLE DECLARATION\n\n⚡ SELLER @{username} | Userid:"
            f" [{user_id}]\n\n✅ SELLER WALLET\n{wallet}\n\nNote: If you don't see"
            " any address, then your address will used from saved addresses after"
            " selecting token and chain for the current escrow."
        )

        await message.answer(text)

        await message.answer(
            "Use /token to Choose crypto."
        )


# ============================================================
# TOKEN
# ============================================================

@dp.message(Command("token"))
async def cmd_token(message: types.Message):

    if message.chat.type in ["group", "supergroup"]:

        get_escrow(message.chat.id)

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
                    ),
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


# ============================================================
# TOKEN CALLBACK
# ============================================================

@dp.callback_query(F.data.startswith("token_"))
async def process_token(callback: types.CallbackQuery):

    token = callback.data.split("_")[1]

    chat_id = callback.message.chat.id

    data = get_escrow(chat_id)

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
            f"📍 ESCROW-CRYPTO DECLARATION\n\n✅ CRYPTO\n{token}\n\nchoose network"
            " from the list below for USDT",
            reply_markup=keyboard
        )

    else:

        data["network"] = "NATIVE"

        await send_final_declaration(
            callback.message,
            chat_id
        )

    await callback.answer()


# ============================================================
# NETWORK
# ============================================================

@dp.callback_query(F.data.startswith("net_"))
async def process_network(callback: types.CallbackQuery):

    network = callback.data.split("_")[1]

    chat_id = callback.message.chat.id

    data = get_escrow(chat_id)

    data["network"] = network

    await send_final_declaration(
        callback.message,
        chat_id
    )

    await callback.answer()


# ============================================================
# BACK TOKEN
# ============================================================

@dp.callback_query(F.data == "back_token")
async def back_token(callback: types.CallbackQuery):

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
                ),
            ],

            [
                InlineKeyboardButton(
                    text="USDT",
                    callback_data="token_USDT"
                )
            ],
        ]
    )

    await callback.message.edit_text(
        "choose token from the list below",
        reply_markup=keyboard
    )

    await callback.answer()


# ============================================================
# FINAL DECLARATION
# ============================================================

async def send_final_declaration(
    message: types.Message,
    chat_id: int
):

    data = get_escrow(chat_id)

    seller = data.get("seller") or "seller"
    seller_id = data.get("seller_id") or "123456"

    buyer = data.get("buyer") or "buyer"
    buyer_id = data.get("buyer_id") or "654321"

    token = data.get("token") or "USDT"
    network = data.get("network") or "BSC"

    text = (
        f"📍 ESCROW DECLARATION\n\n⚡ Seller @{seller} | Userid:"
        f" [{seller_id}]\n⚡ Buyer @{buyer} | Userid:"
        f" [{buyer_id}]\n\n✅ {token} CRYPTO\n✅ {network} NETWORK"
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


# ============================================================
# ACCEPT DEAL
# ============================================================

@dp.callback_query(F.data == "accept_deal")
async def accept_deal(callback: types.CallbackQuery):

    chat_id = callback.message.chat.id

    data = get_escrow(chat_id)

    deal_id = data.get("deal_id", "24153438")

    seller = data.get("seller", "seller")
    seller_id = data.get("seller_id", "111111")
    seller_wallet = data.get(
        "seller_wallet",
        "0x9ae8..."
    )

    buyer = data.get("buyer", "buyer")
    buyer_id = data.get("buyer_id", "222222")
    buyer_wallet = data.get(
        "buyer_wallet",
        "0x1609..."
    )

    token = data.get("token", "USDT")
    network = data.get("network", "BSC")

    data["status"] = "accepted"

    now_str = now_string()

    text = (
        f"📍 TRANSACTION INFORMATION [{deal_id}]\n\n⚡ SELLER\n@{seller} |"
        f" [{seller_id}]\n{seller_wallet}[{token}]\n[{network}]\n\n⚡"
        f" BUYER\n@{buyer} |"
        f" [{buyer_id}]\n{buyer_wallet}[{token}]\n[{network}]\n\n⏰ Trade Start"
        f" Time: {now_str}\n\n⚠️ IMPORTANT: Make sure to finalise and agree"
        " each-others terms before depositing.\n\n📄 Please use /deposit command"
        " to generate a deposit address for your trade."
    )

    await callback.message.edit_text(text)

    await callback.message.answer(
        "Your Fee is 1.0% as both buyer and seller are not using @PagalEscrowBot"
        " in your bio."
    )

    await callback.answer()


# ============================================================
# REJECT DEAL
# ============================================================

@dp.callback_query(F.data == "reject_deal")
async def reject_deal(callback: types.CallbackQuery):

    chat_id = callback.message.chat.id

    data = get_escrow(chat_id)

    data["status"] = "rejected"

    await callback.message.edit_text(
        "❌ ESCROW DEAL REJECTED"
    )

    await callback.answer()


# ============================================================
# DEPOSIT
# ============================================================

@dp.message(Command("deposit"))
async def cmd_deposit(message: types.Message):

    if message.chat.type in ["group", "supergroup"]:

        await message.answer(
            "Requesting a deposit address for you, please wait..."
        )

        await asyncio.sleep(1)

        chat_id = message.chat.id

        data = get_escrow(chat_id)

        deal_id = data.get(
            "deal_id",
            "24153438"
        )

        seller = data.get(
            "seller",
            "seller"
        )

        seller_id = data.get(
            "seller_id",
            "111111"
        )

        buyer = data.get(
            "buyer",
            "buyer"
        )

        buyer_id = data.get(
            "buyer_id",
            "222222"
        )

        token = data.get(
            "token",
            "USDT"
        )

        network = data.get(
            "network",
            "BSC"
        )

        now_str = now_string()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Check Payment",
                        callback_data="check_payment"
                    )
                ]
            ]
        )

        deposit_text = (
            f"📍 TRANSACTION INFORMATION [{deal_id}]\n\n⚡ SELLER\n@{seller} |"
            f" [{seller_id}]\n⚡ BUYER\n@{buyer} | [{buyer_id}]\n🟢 ESCROW"
            " ADDRESS\n0xD3F1F176A39694c8F25F1Df1BAF4E38CcF259ac0"
            f" [{token}]\n[{network}]\n\nSeller [@{seller}] Will Pay on the Escrow"
            " Address, And Click On Check Payment.\n\nAmount Recieved: 0.00000"
            f" [0.00$]\n\n⏰ Trade Start Time: {now_str}\n⏰ Address Reset In:"
            " 20.00 Min\n\n📄 Note: Address will reset after the given time, so"
            " make sure to deposit in the bot before the address expires.\nUseful"
            " commands:\n📄 /release = Will Release The Funds To Buyer.\n📄"
            " /refund = Will Refund The Funds To Seller.\n\nRemember, once commands"
            " a
