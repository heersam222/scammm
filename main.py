
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


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")
if not API_ID:
    raise RuntimeError("API_ID is missing")
if not API_HASH:
    raise RuntimeError("API_HASH is missing")
if not SESSION_STRING:
    raise RuntimeError("SESSION_STRING is missing")

API_ID = int(API_ID)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_client = TelegramClient(
    StringSession(SESSION_STRING),
    API_ID,
    API_HASH,
)

active_escrows = {}


def get_data(chat_id):
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
        },
    )


def person_label(name, username):
    return f"@{username}" if username else name


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.type != "private":
        return

    text = (
        "✨ @PagalEscrowBot ✨\n"
        "Your Trustworthy Telegram Escrow Service\n\n"
        "Welcome to @PagalEscrowBot. This bot provides a reliable escrow service "
        "for your transactions on Telegram.\n"
        "Avoid scams, your funds are safeguarded throughout your deals. If you "
        "run into any issues, simply type /dispute and an arbitrator will join "
        "the group chat within 24 hours.\n\n"
        "🧰 ESCROW FEE:\n"
        "1.0% for P2P and 1.0% for OTC Flat\n\n"
        "🌐 (UPDATES) - (VOUCHES) ✅\n\n"
        "💬 Proceed with /escrow (to start with a new escrow)\n\n"
        "⚠️ IMPORTANT - Make sure coin is same of Buyer and Seller else you "
        "may loose your coin.\n\n"
        "💡 Type /menu to summon a menu with all bots features"
    )

    keyboard = InlineKeyboardMarkup(
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

    await message.answer(text, reply_markup=keyboard)


@dp.message(Command("escrow"))
async def cmd_escrow(message: types.Message):
    if message.chat.type != "private":
        return

    waiting = await message.answer(
        "Creating a safe trading place for you, please wait..."
    )

    try:
        creator = message.from_user
        bot_info = await bot.get_me()

        await user_client.start()

        bot_entity = await user_client.get_entity(f"@{bot_info.username}")

        result = await user_client(
            functions.messages.CreateChatRequest(
                users=[bot_entity],
                title="P2P Escrow By PAGAL Bot",
            )
        )

        created_chat = next(
            (chat for chat in result.chats if isinstance(chat, tg_types.Chat)),
            None,
        )

        if created_chat is None:
            raise RuntimeError("Telegram did not return the new group.")

        invite = await user_client(
            functions.messages.ExportChatInviteRequest(peer=created_chat)
        )

        invite_link = getattr(invite, "link", None)
        if not invite_link:
            raise RuntimeError("Could not create invite link.")

        # Basic Telegram groups use -chat_id in the Bot API.
        chat_id = -created_chat.id

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
            "deal_id": str(creator.id)[-6:],
        }

        response_text = (
            "Escrow Group Created\n\n"
            f"Creator: {creator.full_name}\n\n"
            "Join this escrow group and share the link with the buyer and seller.\n\n"
            f"{invite_link}\n\n"
            "⚠️ Note: This link is for 2 members only—third parties are not allowed to join."
        )

        await waiting.edit_text(response_text)

        welcome = (
            "📍 Hey there traders! Welcome to our escrow service.\n"
            "✅ Please start with /dd command and fill the DealInfo Form"
        )

        sent = await bot.send_message(chat_id=chat_id, text=welcome)

        try:
            await user_client(
                functions.messages.UpdatePinnedMessageRequest(
                    peer=created_chat,
                    id=sent.message_id,
                    silent=True,
                )
            )
        except Exception:
            logging.exception("Pin failed; welcome message was still sent.")

    except Exception as exc:
        logging.exception("Escrow creation failed")
        await waiting.edit_text(
            "❌ Error creating group.\n\n"
            f"Details: {exc}"
        )


@dp.message(Command("dd"))
async def cmd_dd(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return

    text = (
        "Hello there,\n"
        "Kindly tell deal details i.e.\n\n"
        "Quantity -\n"
        "Rate -\n"
        "Conditions (if any) -\n\n"
        "Remember without it disputes wouldn’t be resolved. Once filled proceed "
        "with Specifications of the seller or buyer with /seller or /buyer "
        "[CRYPTO ADDRESS]"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="How To Use Bot ?", callback_data="how_to_use")]
        ]
    )

    await message.answer(text, reply_markup=keyboard)


@dp.message(Command("buyer"))
async def cmd_buyer(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return

    data = get_data(message.chat.id)
    user = message.from_user
    args = message.text.split(maxsplit=1)
    wallet = args[1].strip() if len(args) > 1 else "Saved Address"

    data["buyer"] = user.full_name
    data["buyer_username"] = user.username
    data["buyer_id"] = user.id
    data["buyer_wallet"] = wallet

    username = person_label(user.full_name, user.username)

    text = (
        "📍 ESCROW-ROLE DECLARATION\n\n"
        f"⚡ BUYER {username} | Userid: [{user.id}]\n\n"
        "✅ BUYER WALLET\n"
        f"{wallet}\n\n"
        "Note: If you don't see any address, then your address will used from "
        "saved addresses after selecting token and chain for the current escrow."
    )

    await message.answer(text)
    await message.answer("Please set seller using /seller [DEPOSIT ADDRESS]")


@dp.message(Command("seller"))
async def cmd_seller(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return

    data = get_data(message.chat.id)
    user = message.from_user
    args = message.text.split(maxsplit=1)
    wallet = args[1].strip() if len(args) > 1 else "Saved Address"

    data["seller"] = user.full_name
    data["seller_username"] = user.username
    data["seller_id"] = user.id
    data["seller_wallet"] = wallet

    username = person_label(user.full_name, user.username)

    text = (
        "📍 ESCROW-ROLE DECLARATION\n\n"
        f"⚡ SELLER {username} | Userid: [{user.id}]\n\n"
        "✅ SELLER WALLET\n"
        f"{wallet}\n\n"
        "Note: If you don't see any address, then your address will used from "
        "saved addresses after selecting token and chain for the current escrow."
    )

    await message.answer(text)
    await message.answer("Use /token to Choose crypto.")


@dp.message(Command("token"))
async def cmd_token(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
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
    token = callback.data.split("_", 1)[1]
    chat_id = callback.message.chat.id
    data = get_data(chat_id)
    data["token"] = token

    if token == "USDT":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="BSC[BEP20]", callback_data="net_BSC"),
                    InlineKeyboardButton(text="TRON[TRC20]", callback_data="net_TRON"),
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
        data["network"] = "NATIVE"
        await send_final_declaration(callback.message, chat_id)

    await callback.answer()


@dp.callback_query(F.data.startswith("net_"))
async def process_network(callback: types.CallbackQuery):
    network = callback.data.split("_", 1)[1]
    chat_id = callback.message.chat.id
    data = get_data(chat_id)
    data["network"] = network

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


async def send_final_declaration(message, chat_id):
    data = get_data(chat_id)

    seller = data.get("seller") or "seller"
    seller_id = data.get("seller_id") or "123456"
    buyer = data.get("buyer") or "buyer"
    buyer_id = data.get("buyer_id") or "654321"

    seller_display = person_label(seller, data.get("seller_username"))
    buyer_display = person_label(buyer, data.get("buyer_username"))

    token = data.get("token") or "USDT"
    network = data.get("network") or "BSC"

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
                InlineKeyboardButton(text="Accept ✅", callback_data="accept_deal"),
                InlineKeyboardButton(text="Reject ❌", callback_data="reject_deal"),
            ]
        ]
    )

    await message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(F.data == "accept_deal")
async def accept_deal(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    data = get_data(chat_id)

    deal_id = data.get("deal_id") or "24153438"

    seller = data.get("seller") or "seller"
    seller_id = data.get("seller_id") or "111111"
    seller_wallet = data.get("seller_wallet") or "Saved Address"

    buyer = data.get("buyer") or "buyer"
    buyer_id = data.get("buyer_id") or "222222"
    buyer_wallet = data.get("buyer_wallet") or "Saved Address"

    seller_display = person_label(seller, data.get("seller_username"))
    buyer_display = person_label(buyer, data.get("buyer_username"))

    token = data.get("token") or "USDT"
    network = data.get("network") or "BSC"

    now_str = datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")

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
        "⚠️ IMPORTANT: Make sure to finalise and agree each-others terms before depositing.\n\n"
        "📄 Please use /deposit command to generate a deposit address for your trade."
    )

    await callback.message.edit_text(text)
    await callback.message.answer(
        "Your Fee is 1.0% as both buyer and seller are not using "
        "@PagalEscrowBot in your bio."
    )
    await callback.answer()


@dp.callback_query(F.data == "reject_deal")
async def reject_deal(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Deal rejected.")
    await callback.answer()


@dp.message(Command("deposit"))
async def cmd_deposit(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return

    await message.answer("Requesting a deposit address for you, please wait...")
    await asyncio.sleep(1)

    data = get_data(message.chat.id)

    deal_id = data.get("deal_id") or "24153438"
    seller = data.get("seller") or "seller"
    seller_id = data.get("seller_id") or "111111"
    buyer = data.get("buyer") or "buyer"
    buyer_id = data.get("buyer_id") or "222222"

    seller_display = person_label(seller, data.get("seller_username"))
    buyer_display = person_label(buyer, data.get("buyer_username"))

    token = data.get("token") or "USDT"
    network = data.get("network") or "BSC"

    now_str = datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Check Payment", callback_data="check_payment")]
        ]
    )

    deposit_text = (
        f"📍 TRANSACTION INFORMATION [{deal_id}]\n\n"
        "⚡ SELLER\n"
        f"{seller_display} | [{seller_id}]\n"
        "⚡ BUYER\n"
        f"{buyer_display} | [{buyer_id}]\n"
        "🟢 ESCROW ADDRESS\n"
        "NOT_CONFIGURED\n"
        f"[{token}]\n"
        f"[{network}]\n\n"
        f"Seller [{seller_display}] Will Pay on the Escrow Address, And Click On Check Payment.\n\n"
        "Amount Recieved: 0.00000 [0.00$]\n\n"
        f"⏰ Trade Start Time: {now_str}\n"
        "⏰ Address Reset In: 20.00 Min\n\n"
        "📄 Note: Address will reset after the given time, so make sure to deposit "
        "in the bot before the address expires.\n"
        "Useful commands:\n"
        "📄 /release = Will Release The Funds To Buyer.\n"
        "📄 /refund = Will Refund The Funds To Seller.\n\n"
        "Remember, once commands are used payment will be released, there is no revert!"
    )

    await message.answer(deposit_text, reply_markup=keyboard)


@dp.callback_query(F.data == "check_payment")
async def check_payment(callback: types.CallbackQuery):
    await callback.answer(
        "No payment detected yet. Please deposit funds to the escrow address.",
        show_alert=True,
    )


@dp.message(Command("release"))
async def cmd_release(message: types.Message):
    if message.chat.type in ("group", "supergroup"):
        await message.answer(
            "⚠️ Release request received. Payment verification is required before release."
        )


@dp.message(Command("refund"))
async def cmd_refund(message: types.Message):
    if message.chat.type in ("group", "supergroup"):
        await message.answer(
            "⚠️ Refund request received. Payment verification is required before refund."
        )


@dp.callback_query(F.data == "cmd_list")
async def cmd_list(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "COMMANDS LIST 🤖\n\n"
        "/start\n"
        "/escrow\n"
        "/dd\n"
        "/buyer\n"
        "/seller\n"
        "/token\n"
        "/deposit\n"
        "/release\n"
        "/refund\n"
        "/dispute"
    )


@dp.callback_query(F.data == "contact")
async def contact(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("📞 CONTACT")


@dp.callback_query(F.data == "updates")
async def updates(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("🔄 Updates")


@dp.callback_query(F.data == "vouches")
async def vouches(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("✅ Vouches")


@dp.callback_query(F.data == "what_is_escrow")
async def what_is_escrow(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "WHAT IS ESCROW ?\n\n"
        "Escrow is a transaction arrangement where funds are held until the "
        "agreed conditions of a deal are completed."
    )


@dp.callback_query(F.data == "instructions")
async def instructions(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("Instructions 👩‍💻")


@dp.callback_query(F.data == "terms")
async def terms(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("Terms 📝")


@dp.callback_query(F.data == "invites")
async def invites(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("Invites 👤")


@dp.callback_query(F.data == "how_to_use")
async def how_to_use(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "How To Use Bot ?\n\nStart with /dd and follow the instructions."
    )


@dp.callback_query(F.data.in_(["start_p2p", "start_product"]))
async def start_deal(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "Please use /escrow to start with a new escrow."
    )


@dp.message(Command("dispute"))
async def cmd_dispute(message: types.Message):
    if message.chat.type in ("group", "supergroup"):
        await message.answer("⚠️ Dispute request received.")


async def main():
    await user_client.start()

    me = await user_client.get_me()
    logging.info(
        "User session connected: %s [%s]",
        getattr(me, "first_name", "Unknown"),
        me.id,
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
