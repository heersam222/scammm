import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ============================================================
# PAGAL ESCROW — UI/WORKFLOW DEMO
# ------------------------------------------------------------
# This version intentionally does NOT move, hold, verify, or
# release real cryptocurrency. It reproduces the Telegram
# workflow/UI shown in the screenshots for testing.
#
# Set your bot token as an environment variable:
#   BOT_TOKEN=123456:ABC...
# ============================================================

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

if TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise RuntimeError("Set BOT_TOKEN environment variable before running.")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())


@dataclass
class Escrow:
    creator_id: int
    creator_name: str
    buyer: str | None = None
    buyer_id: int | None = None
    buyer_wallet: str | None = None
    seller: str | None = None
    seller_id: int | None = None
    seller_wallet: str | None = None
    token: str | None = None
    network: str | None = None
    deal_id: str = ""
    quantity: str = ""
    rate: str = ""
    conditions: str = ""


active_escrows: dict[int, Escrow] = {}


def display_name(user: types.User) -> str:
    return f"@{user.username}" if user.username else user.full_name


def menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="COMMANDS LIST 🤖", callback_data="cmd_list")],
            [InlineKeyboardButton(text="📞 CONTACT", callback_data="contact")],
            [
                InlineKeyboardButton(text="Updates 🔄", callback_data="updates"),
                InlineKeyboardButton(text="Vouches ✅", callback_data="vouches"),
            ],
            [
                InlineKeyboardButton(text="WHAT IS ESCROW ?", callback_data="what_is_escrow"),
                InlineKeyboardButton(text="Instructions 👩‍💻", callback_data="instructions"),
            ],
            [InlineKeyboardButton(text="Terms 📝", callback_data="terms")],
            [InlineKeyboardButton(text="Invites 👤", callback_data="invites")],
            [
                InlineKeyboardButton(text="P2P", callback_data="start_p2p"),
                InlineKeyboardButton(text="Product Deal", callback_data="start_product"),
            ],
        ]
    )


START_TEXT = (
    "✨ @PagalEscrowBot ✨\n"
    "Your Trustworthy Telegram Escrow Service\n\n"
    "Welcome to @PagalEscrowBot. This bot provides a Telegram escrow "
    "workflow for testing.\n\n"
    "⚠️ DEMO MODE: This bot does not hold, transfer, or verify real crypto.\n\n"
    "🧰 ESCROW FEE:\n"
    "1.0% for P2P and 1.0% for OTC Flat\n\n"
    "🌐 (UPDATES) - (VOUCHES) ✅\n\n"
    "💬 Proceed with /escrow (to start a new demo escrow)\n\n"
    "⚠️ IMPORTANT - Use only test data in this demo.\n\n"
    "💡 Type /menu to summon a menu with all bot features"
)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.type != "private":
        return
    await message.answer(START_TEXT, reply_markup=menu_keyboard())


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    if message.chat.type != "private":
        return
    await message.answer("Please select your escrow type from below.", reply_markup=menu_keyboard())


@dp.message(Command("escrow"))
async def cmd_escrow(message: types.Message):
    if message.chat.type != "private":
        return

    await message.answer(
        "Creating a safe trading place for you, please wait..."
    )

    await asyncio.sleep(0.5)

    # Telegram Bot API does not provide bot.create_chat().
    # The group must be created by a user and the bot added to it.
    await message.answer(
        "Escrow Group Setup\n\n"
        "1. Create a Telegram supergroup.\n"
        "2. Add this bot as an administrator.\n"
        "3. Add the buyer and seller.\n"
        "4. Run /setup in that group.\n\n"
        "⚠️ DEMO MODE: no real funds are handled."
    )


@dp.message(Command("setup"))
async def cmd_setup(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    user = message.from_user
    active_escrows[message.chat.id] = Escrow(
        creator_id=user.id,
        creator_name=user.full_name,
        deal_id=str(user.id)[-6:],
    )

    await message.answer(
        "Escrow Group Created\n\n"
        f"Creator: {user.full_name}\n\n"
        "Join this escrow group and share the group with the buyer and seller.\n\n"
        "⚠️ Note: This is a demo workflow. No real crypto is processed."
    )


@dp.message(Command("dd"))
async def cmd_dd(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    await message.answer(
        "Hello there,\n"
        "Kindly tell deal details i.e.\n\n"
        "Quantity -\n"
        "Rate -\n"
        "Conditions (if any) -\n\n"
        "Remember without it disputes wouldn’t be resolved. "
        "Once filled proceed with Specifications of the seller or "
        "buyer with /seller or /buyer [CRYPTO ADDRESS]\n\n"
        "⚠️ DEMO MODE — use a placeholder address, not a real wallet."
    )


@dp.message(Command("buyer"))
async def cmd_buyer(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    chat_id = message.chat.id
    escrow = active_escrows.setdefault(
        chat_id,
        Escrow(
            creator_id=message.from_user.id,
            creator_name=message.from_user.full_name,
            deal_id=str(message.from_user.id)[-6:],
        ),
    )

    args = message.text.split(maxsplit=1)
    wallet = args[1].strip() if len(args) > 1 else "Saved Address (DEMO)"

    escrow.buyer = display_name(message.from_user)
    escrow.buyer_id = message.from_user.id
    escrow.buyer_wallet = wallet

    await message.answer(
        "📍 ESCROW-ROLE DECLARATION\n\n"
        f"⚡ BUYER {escrow.buyer} | Userid: [{escrow.buyer_id}]\n\n"
        "✅ BUYER WALLET\n"
        f"{wallet}\n\n"
        "Note: If you don't see any address, then your address will used "
        "from saved addresses after selecting token and chain for the current escrow.\n\n"
        "⚠️ DEMO MODE — no real wallet is used."
    )
    await message.answer("Please set seller using /seller [DEPOSIT ADDRESS]")


@dp.message(Command("seller"))
async def cmd_seller(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    chat_id = message.chat.id
    escrow = active_escrows.setdefault(
        chat_id,
        Escrow(
            creator_id=message.from_user.id,
            creator_name=message.from_user.full_name,
            deal_id=str(message.from_user.id)[-6:],
        ),
    )

    args = message.text.split(maxsplit=1)
    wallet = args[1].strip() if len(args) > 1 else "Saved Address (DEMO)"

    escrow.seller = display_name(message.from_user)
    escrow.seller_id = message.from_user.id
    escrow.seller_wallet = wallet

    await message.answer(
        "📍 ESCROW-ROLE DECLARATION\n\n"
        f"⚡ SELLER {escrow.seller} | Userid: [{escrow.seller_id}]\n\n"
        "✅ SELLER WALLET\n"
        f"{wallet}\n\n"
        "Note: If you don't see any address, then your address will used "
        "from saved addresses after selecting token and chain for the current escrow.\n\n"
        "⚠️ DEMO MODE — no real wallet is used."
    )
    await message.answer("Use /token to Choose crypto.")


@dp.message(Command("token"))
async def cmd_token(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="LTC", callback_data="token_LTC"),
                InlineKeyboardButton(text="BTC", callback_data="token_BTC"),
            ],
            [InlineKeyboardButton(text="USDT", callback_data="token_USDT")],
        ]
    )
    await message.answer(
        "choose token from the list below",
        reply_markup=keyboard,
    )


@dp.callback_query(F.data.startswith("token_"))
async def process_token(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    escrow = active_escrows.setdefault(
        chat_id,
        Escrow(
            creator_id=callback.from_user.id,
            creator_name=callback.from_user.full_name,
            deal_id=str(callback.from_user.id)[-6:],
        ),
    )

    token = callback.data.split("_", 1)[1]
    escrow.token = token

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
                [InlineKeyboardButton(text="Back ⬅️", callback_data="back_token")],
            ]
        )
        await callback.message.edit_text(
            "📍 ESCROW-CRYPTO DECLARATION\n\n"
            f"✅ CRYPTO\n{token}\n\n"
            "choose network from the list below for USDT",
            reply_markup=keyboard,
        )
    else:
        escrow.network = "NATIVE"
        await send_final_declaration(callback.message, chat_id)

    await callback.answer()


@dp.callback_query(F.data == "back_token")
async def back_token(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="LTC", callback_data="token_LTC"),
                InlineKeyboardButton(text="BTC", callback_data="token_BTC"),
            ],
            [InlineKeyboardButton(text="USDT", callback_data="token_USDT")],
        ]
    )
    await callback.message.edit_text(
        "choose token from the list below",
        reply_markup=keyboard,
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("net_"))
async def process_network(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    escrow = active_escrows[chat_id]
    escrow.network = callback.data.split("_", 1)[1]

    await send_final_declaration(callback.message, chat_id)
    await callback.answer()


async def send_final_declaration(message: types.Message, chat_id: int):
    escrow = active_escrows[chat_id]

    seller = escrow.seller or "seller"
    buyer = escrow.buyer or "buyer"
    seller_id = escrow.seller_id or "—"
    buyer_id = escrow.buyer_id or "—"
    token = escrow.token or "USDT"
    network = escrow.network or "BSC"

    text = (
        "📍 ESCROW DECLARATION\n\n"
        f"⚡ Seller {seller} | Userid: [{seller_id}]\n"
        f"⚡ Buyer {buyer} | Userid: [{buyer_id}]\n\n"
        f"✅ {token} CRYPTO\n"
        f"✅ {network} NETWORK\n\n"
        "⚠️ DEMO MODE — no real transaction will be executed."
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

    await message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(F.data == "reject_deal")
async def reject_deal(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "❌ Escrow declaration rejected.\n\n"
        "You can restart the demo flow with /token."
    )
    await callback.answer()


@dp.callback_query(F.data == "accept_deal")
async def accept_deal(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    escrow = active_escrows.get(chat_id)

    if not escrow:
        await callback.answer("Escrow session not found.", show_alert=True)
        return

    now_str = datetime.now().strftime("%d/%m/%y %H:%M:%S")

    text = (
        f"📍 TRANSACTION INFORMATION [{escrow.deal_id}]\n\n"
        "⚡ SELLER\n"
        f"{escrow.seller or 'seller'} | [{escrow.seller_id or '—'}]\n"
        f"{escrow.seller_wallet or 'DEMO_ADDRESS'}[{escrow.token or 'USDT'}]\n"
        f"[{escrow.network or 'BSC'}]\n\n"
        "⚡ BUYER\n"
        f"{escrow.buyer or 'buyer'} | [{escrow.buyer_id or '—'}]\n"
        f"{escrow.buyer_wallet or 'DEMO_ADDRESS'}[{escrow.token or 'USDT'}]\n"
        f"[{escrow.network or 'BSC'}]\n\n"
        f"⏰ Trade Start Time: {now_str}\n\n"
        "⚠️ IMPORTANT: Make sure to finalise and agree each-others terms "
        "before proceeding.\n\n"
        "📄 DEMO: /deposit shows a simulated deposit screen only."
    )

    await callback.message.edit_text(text)
    await callback.message.answer(
        "⚠️ DEMO MODE\n"
        "No real payment, deposit, release, refund, or blockchain check "
        "is performed by this bot."
    )
    await callback.answer()


@dp.message(Command("deposit"))
async def cmd_deposit(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    escrow = active_escrows.get(message.chat.id)
    if not escrow:
        await message.answer("Start the demo with /setup first.")
        return

    await message.answer("Requesting a demo deposit screen, please wait...")
    await asyncio.sleep(0.5)

    now_str = datetime.now().strftime("%d/%m/%y %H:%M:%S")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Check Payment",
                    callback_data="check_payment",
                )
            ]
        ]
    )

    deposit_text = (
        f"📍 TRANSACTION INFORMATION [{escrow.deal_id}]\n\n"
        "⚡ SELLER\n"
        f"{escrow.seller or 'seller'} | [{escrow.seller_id or '—'}]\n"
        "⚡ BUYER\n"
        f"{escrow.buyer or 'buyer'} | [{escrow.buyer_id or '—'}]\n"
        "🟢 ESCROW ADDRESS\n"
        "DEMO_ADDRESS_NOT_A_REAL_WALLET\n"
        f"[{escrow.token or 'USDT'}]\n"
        f"[{escrow.network or 'BSC'}]\n\n"
        "Seller will see a simulated deposit screen here.\n\n"
        "Amount Received: 0.00000 [0.00$]\n\n"
        f"⏰ Trade Start Time: {now_str}\n"
        "⏰ Address Reset In: 20.00 Min\n\n"
        "📄 Note: This is a UI simulation. No address is generated and "
        "no blockchain payment is checked.\n\n"
        "Useful demo commands:\n"
        "📄 /release = simulated release screen.\n"
        "📄 /refund = simulated refund screen."
    )

    await message.answer(deposit_text, reply_markup=keyboard)


@dp.callback_query(F.data == "check_payment")
async def check_payment_callback(callback: types.CallbackQuery):
    await callback.answer(
        "DEMO: No real payment is checked.",
        show_alert=True,
    )


@dp.message(Command("release"))
async def cmd_release(message: types.Message):
    if message.chat.type in {"group", "supergroup"}:
        await message.answer(
            "✅ DEMO: Funds-release screen completed.\n"
            "No real funds were released."
        )


@dp.message(Command("refund"))
async def cmd_refund(message: types.Message):
    if message.chat.type in {"group", "supergroup"}:
        await message.answer(
            "🔄 DEMO: Refund screen completed.\n"
            "No real funds were refunded."
        )


# -------------------- MENU CALLBACKS --------------------

MENU_TEXT = {
    "cmd_list": (
        "🤖 COMMANDS LIST\n\n"
        "/start — Start bot\n"
        "/menu — Open menu\n"
        "/escrow — Demo escrow setup\n"
        "/setup — Initialize current group\n"
        "/dd — DealInfo form\n"
        "/buyer — Set buyer\n"
        "/seller — Set seller\n"
        "/token — Choose crypto\n"
        "/deposit — Simulated deposit screen\n"
        "/release — Simulated release\n"
        "/refund — Simulated refund"
    ),
    "contact": "📞 CONTACT\n\nDemo support: use the bot owner/admin contact configured for your project.",
    "updates": "🔄 UPDATES\n\nDemo build — no live payment functionality.",
    "vouches": "✅ VOUCHES\n\nDemo mode: no real transaction history.",
    "what_is_escrow": (
        "WHAT IS ESCROW ?\n\n"
        "Escrow is a process where a neutral party can hold an asset "
        "until agreed conditions are met. This project only demonstrates "
        "the interface and workflow."
    ),
    "instructions": (
        "👩‍💻 Instructions\n\n"
        "Create a supergroup manually, add the bot as an administrator, "
        "then use /setup. Continue with /dd, /buyer, /seller and /token."
    ),
    "terms": (
        "📝 Terms\n\n"
        "This build is a software demo. It does not custody, transfer, "
        "verify, or release cryptocurrency."
    ),
    "invites": "👤 Invites\n\nUse Telegram's normal group invite controls for this demo.",
    "start_p2p": "P2P demo selected. Create a group and use /setup.",
    "start_product": "Product Deal demo selected.",
    "how_to_use": (
        "How To Use Bot ?\n\n"
        "1. /setup\n"
        "2. /dd\n"
        "3. /buyer <demo-address>\n"
        "4. /seller <demo-address>\n"
        "5. /token\n"
        "6. Accept the demo declaration\n"
        "7. /deposit\n"
    ),
}


@dp.callback_query(F.data.in_(MENU_TEXT.keys()))
async def menu_callbacks(callback: types.CallbackQuery):
    await callback.message.answer(MENU_TEXT[callback.data])
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    
