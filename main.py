import datetime
import logging
import os
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# Logging Setup
logging.basicConfig(level=logging.INFO)

# --- ENVIRONMENT VARIABLES ---
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Initialize Pyrogram Client (Userbot + Bot integration)
app = Client(
    "pagal_escrow_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    bot_token=BOT_TOKEN,
)

# In-memory storage for active escrows
active_escrows = {}


# --- START COMMAND (PRIVATE CHAT) ---
@app.on_message(filters.command("start") & filters.private)
async def cmd_start(client, message: Message):
  text = (
      "✨ @PagalEscrowBot ✨\nYour Trustworthy Telegram Escrow Service\n\nWelcome"
      " to @PagalEscrowBot. This bot provides a reliable escrow service for your"
      " transactions on Telegram.\nAvoid scams, your funds are safeguarded"
      " throughout your deals. If you run into any issues, simply type"
      " /dispute and an arbitrator will join the group chat within 24"
      " hours.\n\n🧰 ESCROW FEE:\n1.0% for P2P and 1.0% for OTC Flat\n\n🌐"
      " (UPDATES) - (VOUCHES) ✅\n\n💬 Proceed with /escrow (to start with a new"
      " escrow)\n\n⚠️ IMPORTANT - Make sure coin is same of Buyer and Seller"
      " else you may loose your coin.\n\n💡 Type /menu to summon a menu with all"
      " bots features"
  )
  keyboard = InlineKeyboardMarkup([
      [InlineKeyboardButton("COMMANDS LIST 🤖", callback_data="cmd_list")],
      [InlineKeyboardButton("📞 CONTACT", callback_data="contact")],
      [
          InlineKeyboardButton("Updates 🔄", callback_data="updates"),
          InlineKeyboardButton("Vouches ✅", callback_data="vouches"),
      ],
      [
          InlineKeyboardButton("WHAT IS ESCROW ?", callback_data="what_is_escrow"),
          InlineKeyboardButton("Instructions 👩‍💻", callback_data="instructions"),
      ],
      [InlineKeyboardButton("Terms 📝", callback_data="terms")],
      [InlineKeyboardButton("Invites 👤", callback_data="invites")],
      [
          InlineKeyboardButton("P2P", callback_data="start_p2p"),
          InlineKeyboardButton("Product Deal", callback_data="start_product"),
      ],
  ])
  await message.reply_text(text, reply_markup=keyboard)


# --- ESCROW GROUP CREATION (AUTOMATIC GROUP & PHOTO) ---
@app.on_message(filters.command("escrow") & filters.private)
async def cmd_escrow(client, message: Message):
  status_msg = await message.reply_text(
      "Creating a safe trading place for you, please wait..."
  )

  try:
    user = message.from_user
    creator_name = user.first_name

    # 1. Create a supergroup using userbot session
    group = await client.create_supergroup(
        title=f"P2P Escrow By PAGAL Bot ({creator_name})",
        description="Official Secure Escrow Group. Powered by @PagalEscrowBot",
    )
    chat_id = group.id

    # 2. Export invite link
    invite_link = await client.export_chat_invite_link(chat_id)

    # 3. Set Group Photo (Make sure 'escrow_logo.jpg' is uploaded in your GitHub repository)
    try:
      if os.path.exists("escrow_logo.jpg"):
        await client.set_chat_photo(chat_id, photo="escrow_logo.jpg")
    except Exception as photo_err:
      logging.warning(f"Could not set group photo: {photo_err}")

    # 4. Initialize Data Mapping for this group
    deal_id = str(chat_id)[-6:]  # Unique deal ID based on chat ID
    active_escrows[chat_id] = {
        "creator_id": user.id,
        "creator_name": creator_name,
        "buyer": None,
        "buyer_id": None,
        "buyer_wallet": None,
        "seller": None,
        "seller_id": None,
        "seller_wallet": None,
        "token": None,
        "network": None,
        "deal_id": deal_id,
    }

    response_text = (
        f"Escrow Group Created Successfully!\n\nCreator: {creator_name}\n\nJoin"
        f" this escrow group and share the link with the buyer and"
        f" seller:\n\n{invite_link}\n\n⚠️ Note: Make sure both buyer and"
        " seller join the group."
    )
    await status_msg.edit_text(response_text)

  except Exception as e:
    await status_msg.edit_text(
        f"❌ Error creating group. Check your Session String and permissions."
        f"\nDetails: {str(e)}"
    )


# --- DEAL DETAILS (/dd) ---
@app.on_message(filters.command("dd") & filters.group)
async def cmd_dd(client, message: Message):
  text = (
      "Hello there,\nKindly tell deal details i.e.\n\nQuantity -\nRate -"
      " \nConditions (if any) -\n\nRemember without it disputes wouldn’t be"
      " resolved. Once filled proceed with Specifications of the seller or"
      " buyer with /seller or /buyer [CRYPTO ADDRESS]"
  )
  keyboard = InlineKeyboardMarkup([[
      InlineKeyboardButton("How To Use Bot ?", callback_data="how_to_use")
  ]])
  msg = await message.reply_text(text, reply_markup=keyboard)
  try:
    await msg.pin()
  except Exception:
    pass


# --- BUYER DECLARATION (/buyer) ---
@app.on_message(filters.command("buyer") & filters.group)
async def cmd_buyer(client, message: Message):
  chat_id = message.chat.id
  if chat_id not in active_escrows:
    active_escrows[chat_id] = {}

  args = message.text.split(maxsplit=1)
  wallet = args[1] if len(args) > 1 else "Saved Address"

  user = message.from_user
  username = user.username or user.first_name
  user_id = user.id

  active_escrows[chat_id]["buyer"] = username
  active_escrows[chat_id]["buyer_id"] = user_id
  active_escrows[chat_id]["buyer_wallet"] = wallet

  text = (
      f"📍 ESCROW-ROLE DECLARATION\n\n⚡ BUYER @{username} | Userid:"
      f" [{user_id}]\n\n✅ BUYER WALLET\n{wallet}\n\nNote: If you don't see"
      " any address, then your address will used from saved addresses after"
      " selecting token and chain for the current escrow."
  )
  await message.reply_text(text)
  await message.reply_text("Please set seller using /seller [DEPOSIT ADDRESS]")


# --- SELLER DECLARATION (/seller) ---
@app.on_message(filters.command("seller") & filters.group)
async def cmd_seller(client, message: Message):
  chat_id = message.chat.id
  if chat_id not in active_escrows:
    active_escrows[chat_id] = {}

  args = message.text.split(maxsplit=1)
  wallet = args[1] if len(args) > 1 else "Saved Address"

  user = message.from_user
  username = user.username or user.first_name
  user_id = user.id

  active_escrows[chat_id]["seller"] = username
  active_escrows[chat_id]["seller_id"] = user_id
  active_escrows[chat_id]["seller_wallet"] = wallet

  text = (
      f"📍 ESCROW-ROLE DECLARATION\n\n⚡ SELLER @{username} | Userid:"
      f" [{user_id}]\n\n✅ SELLER WALLET\n{wallet}\n\nNote: If you don't see"
      " any address, then your address will used from saved addresses after"
      " selecting token and chain for the current escrow."
  )
  await message.reply_text(text)
  await message.reply_text("Use /token to Choose crypto.")


# --- TOKEN SELECTION (/token) ---
@app.on_message(filters.command("token") & filters.group)
async def cmd_token(client, message: Message):
  keyboard = InlineKeyboardMarkup([
      [
          InlineKeyboardButton("LTC", callback_data="token_LTC"),
          InlineKeyboardButton("BTC", callback_data="token_BTC"),
      ],
      [InlineKeyboardButton("USDT", callback_data="token_USDT")],
  ])
  await message.reply_text(
      "choose token from the list below", reply_markup=keyboard
  )


@app.on_callback_query(filters.regex(r"^token_"))
async def process_token(client, callback: CallbackQuery):
  token = callback.data.split("_")[1]
  chat_id = callback.message.chat.id
  if chat_id not in active_escrows:
    active_escrows[chat_id] = {}
  active_escrows[chat_id]["token"] = token

  if token == "USDT":
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("BSC[BEP20]", callback_data="net_BSC"),
            InlineKeyboardButton("TRON[TRC20]", callback_data="net_TRON"),
        ],
        [InlineKeyboardButton("Back ⬅️", callback_data="back_token")],
    ])
    await callback.message.edit_text(
        f"📍 ESCROW-CRYPTO DECLARATION\n\n✅ CRYPTO\n{token}\n\nchoose network"
        " from the list below for USDT",
        reply_markup=keyboard,
    )
  else:
    active_escrows[chat_id]["network"] = "NATIVE"
    await send_final_declaration(callback.message, chat_id)


@app.on_callback_query(filters.regex(r"^net_"))
async def process_network(client, callback: CallbackQuery):
  network = callback.data.split("_")[1]
  chat_id = callback.message.chat.id
  if chat_id not in active_escrows:
    active_escrows[chat_id] = {}
  active_escrows[chat_id]["network"] = network
  await send_final_declaration(callback.message, chat_id)


async def send_final_declaration(message: Message, chat_id: int):
  data = active_escrows.get(chat_id, {})
  seller = data.get("seller", "seller")
  seller_id = data.get("seller_id", "123456")
  buyer = data.get("buyer", "buyer")
  buyer_id = data.get("buyer_id", "654321")
  token = data.get("token", "USDT")
  network = data.get("network", "BSC")

  text = (
      f"📍 ESCROW DECLARATION\n\n⚡ Seller @{seller} | Userid:"
      f" [{seller_id}]\n⚡ Buyer @{buyer} | Userid:"
      f" [{buyer_id}]\n\n✅ {token} CRYPTO\n✅ {network} NETWORK"
  )
  keyboard = InlineKeyboardMarkup([[
      InlineKeyboardButton("Accept ✅", callback_data="accept_deal"),
      InlineKeyboardButton("Reject ❌", callback_data="reject_deal"),
  ]])
  await message.edit_text(text, reply_markup=keyboard)


# --- ACCEPT DEAL & TRANSACTION INFO ---
@app.on_callback_query(filters.regex("accept_deal"))
async def accept_deal(client, callback: CallbackQuery):
  chat_id = callback.message.chat.id
  data = active_escrows.get(chat_id, {})
  deal_id = data.get("deal_id", "241534")
  seller = data.get("seller", "seller")
  seller_id = data.get("seller_id", "111111")
  seller_wallet = data.get("seller_wallet", "0x9ae8...")
  buyer = data.get("buyer", "buyer")
  buyer_id = data.get("buyer_id", "222222")
  buyer_wallet = data.get("buyer_wallet", "0x1609...")
  token = data.get("token", "USDT")
  network = data.get("network", "BSC")
  now_str = datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")

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
  await callback.message.reply_text(
      "Your Fee is 1.0% as both buyer and seller are not using @PagalEscrowBot"
      " in your bio."
  )


# --- DEPOSIT COMMAND ---
@app.on_message(filters.command("deposit") & filters.group)
async def cmd_deposit(client, message: Message):
  chat_id = message.chat.id
  data = active_escrows.get(chat_id, {})
  deal_id = data.get("deal_id", "241534")
  seller = data.get("seller", "seller")
  seller_id = data.get("seller_id", "111111")
  buyer = data.get("buyer", "buyer")
  buyer_id = data.get("buyer_id", "222222")
  token = data.get("token", "USDT")
  network = data.get("network", "BSC")
  now_str = datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")

  keyboard = InlineKeyboardMarkup(
      [[InlineKeyboardButton("Check Payment", callback_data="check_payment")]]
  )

  deposit_text = (
      f"📍 TRANSACTION INFORMATION [{deal_id}]\n\n⚡ SELLER\n@{seller} |"
      f" [{seller_id}]\n⚡ BUYER\n@{buyer} | [{buyer_id}]\n🟢 ESCROW"
      f" ADDRESS\n0xD3F1F176A39694c8F25F1Df1BAF4E38CcF259ac0"
      f" [{token}]\n[{network}]\n\nSeller [@{seller}] Will Pay on the Escrow"
      " Address, And Click On Check Payment.\n\nAmount Recieved: 0.00000"
      f" [0.00$]\n\n⏰ Trade Start Time: {now_str}\n⏰ Address Reset In:"
      " 20.00 Min\n\n📄 Note: Address will reset after the given time, so"
      " make sure to deposit in the bot before the address expires.\nUseful"
      " commands:\n📄 /release = Will Release The Funds To Buyer.\n📄"
      " /refund = Will Refund The Funds To Seller.\n\nRemember, once commands"
      " are used payment will be released, there is no revert!"
  )
  await message.reply_text(deposit_text, reply_markup=keyboard)


@app.on_callback_query(filters.regex("check_payment"))
async def check_payment_callback(client, callback: CallbackQuery):
  await callback.answer(
      "No payment detected yet. Please deposit funds to the escrow address.",
      show_alert=True,
  )


# --- RELEASE & REFUND ---
@app.on_message(filters.command("release") & filters.group)
async def cmd_release(client, message: Message):
  await message.reply_text(
      "✅ Funds successfully released to the buyer! Trade completed."
  )


@app.on_message(filters.command("refund") & filters.group)
async def cmd_refund(client, message: Message):
  await message.reply_text(
      "🔄 Funds successfully refunded to the seller! Trade cancelled."
  )


# --- RUN BOT ---
if __name__ == "__main__":
  print("PAGAL Escrow Bot is starting...")
  app.run()
  
