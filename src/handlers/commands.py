import os
import random
import re
import aiohttp
import base58
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.filters.command import CommandStart
from aiogram.enums import ParseMode, ChatType

from src.database import db

router = Router()

MAX_BUY_AMOUNT = 10000  # Max cm per purchase (1 FAPCOIN = 1 cm)
QUICK_BUY_OPTIONS = [500, 1000, 2500, 5000, 10000]  # Quick buy buttons


def is_owner(telegram_id: int) -> bool:
    """Check if user is the bot owner."""
    owner_id = os.environ.get('OWNER_ID', '')
    if not owner_id:
        return False
    try:
        return int(owner_id) == telegram_id
    except ValueError:
        return False


def get_main_menu_keyboard(bot_username: str = None, is_private: bool = False):
    if is_private or not bot_username:
        buy_button = InlineKeyboardButton(text="💰 Buy Growth", callback_data="action_buy")
    else:
        buy_button = InlineKeyboardButton(text="💰 Buy Growth", url=f"https://t.me/{bot_username}?start=buy")
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌱 Grow", callback_data="action_grow"),
            InlineKeyboardButton(text="🏆 Leaderboard", callback_data="action_top")
        ],
        [
            InlineKeyboardButton(text="⚔️ PvP Battle", callback_data="action_pvp_info"),
            InlineKeyboardButton(text="🎲 Daily Winner", callback_data="action_daily")
        ],
        [
            buy_button,
            InlineKeyboardButton(text="💝 Gift", callback_data="action_gift_info")
        ],
        [
            InlineKeyboardButton(text="📊 My Stats", callback_data="action_stats"),
            InlineKeyboardButton(text="💳 Loan", callback_data="action_loan")
        ],
        [
            InlineKeyboardButton(text="❓ Help", callback_data="action_help")
        ],
        [
            InlineKeyboardButton(text="🆘 Support", callback_data="action_support")
        ]
    ])


def get_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="action_menu")]
    ])


def get_buy_keyboard():
    """Get keyboard with quick buy options (1:1 ratio)."""
    buttons = []
    row = []
    for amount in QUICK_BUY_OPTIONS:
        row.append(InlineKeyboardButton(
            text=f"+{amount} cm",
            callback_data=f"buy_amount_{amount}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="📝 Custom Amount", callback_data="buy_custom")])
    buttons.append([InlineKeyboardButton(text="◀️ Back to Menu", callback_data="action_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def validate_solana_tx_hash(tx_hash: str) -> bool:
    if len(tx_hash) < 43 or len(tx_hash) > 100:
        return False
    try:
        decoded = base58.b58decode(tx_hash)
        return len(decoded) >= 32
    except:
        return False


def validate_solana_address(address: str) -> bool:
    if len(address) < 32 or len(address) > 44:
        return False
    try:
        decoded = base58.b58decode(address)
        if len(decoded) != 32:
            return False
        return True
    except:
        return False


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_chat(event: ChatMemberUpdated):
    if event.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Start Playing", callback_data="action_menu")]
        ])
        await event.answer(
            "🎉 <b>FAPCOIN DICK BOT has joined!</b> 🎉\n\n"
            "Welcome to the ultimate growth competition!\n\n"
            "🌱 Grow daily • 🏆 Compete • ⚔️ Battle friends\n\n"
            "Click below to start playing!",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_param(message: Message, bot: Bot):
    args = message.text.split()
    param = args[1] if len(args) > 1 else None
    
    await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    if param == "buy":
        await message.answer(
            "💰 <b>GROWTH PACKAGES</b> 💰\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Buy growth with <b>$FAPCOIN</b>!\n"
            "Select a package below:\n"
            "━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=await get_packages_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return
    
    name = message.from_user.first_name or "Player"
    bot_info = await bot.get_me()
    is_private = message.chat.type == ChatType.PRIVATE
    
    await message.answer(
        f"🍆 <b>Welcome, {name}!</b> 🍆\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "       <b>FAPCOIN DICK BOT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎮 <b>Grow your length daily</b>\n"
        "🏆 <b>Compete on leaderboards</b>\n"
        "⚔️ <b>Battle friends in PvP</b>\n"
        "💰 <b>Buy growth with $FAPCOIN</b>\n\n"
        "Select an option below to begin:",
        reply_markup=get_main_menu_keyboard(bot_info.username, is_private),
        parse_mode=ParseMode.HTML
    )


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    name = message.from_user.first_name or "Player"
    bot_info = await bot.get_me()
    is_private = message.chat.type == ChatType.PRIVATE
    
    await message.answer(
        f"🍆 <b>Welcome, {name}!</b> 🍆\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "       <b>FAPCOIN DICK BOT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎮 <b>Grow your length daily</b>\n"
        "🏆 <b>Compete on leaderboards</b>\n"
        "⚔️ <b>Battle friends in PvP</b>\n"
        "💰 <b>Buy growth with $FAPCOIN</b>\n\n"
        "Select an option below to begin:",
        reply_markup=get_main_menu_keyboard(bot_info.username, is_private),
        parse_mode=ParseMode.HTML
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, bot: Bot):
    bot_info = await bot.get_me()
    is_private = message.chat.type == ChatType.PRIVATE
    
    await message.answer(
        "🎮 <b>Main Menu</b>\n\n"
        "Select an option:",
        reply_markup=get_main_menu_keyboard(bot_info.username, is_private),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "action_menu")
async def callback_menu(callback: CallbackQuery, bot: Bot):
    bot_info = await bot.get_me()
    is_private = callback.message.chat.type == ChatType.PRIVATE
    
    await callback.message.edit_text(
        "🎮 <b>Main Menu</b>\n\n"
        "Select an option:",
        reply_markup=get_main_menu_keyboard(bot_info.username, is_private),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin panel - owner only."""
    telegram_id = message.from_user.id
    
    if not is_owner(telegram_id):
        await message.answer("❌ This command is only for the bot owner.", parse_mode=None)
        return
    
    current_wallet = await db.get_team_wallet() or os.environ.get('TEAM_WALLET_ADDRESS', 'Not set')
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Set Team Wallet", callback_data="admin_setwallet")],
        [InlineKeyboardButton(text="💵 Set Prices", callback_data="admin_setprices")],
        [InlineKeyboardButton(text="📊 View Stats", callback_data="admin_stats")],
    ])
    
    await message.answer(
        f"🔐 <b>ADMIN PANEL</b> 🔐\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Owner ID: <code>{telegram_id}</code>\n"
        f"💰 Team Wallet:\n<code>{current_wallet}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Commands:</b>\n"
        f"/setwallet [address] - Set team wallet\n"
        f"/setprice [pkg] [price] - Set package price\n"
        f"/setgrowth [pkg] [cm] - Set package growth\n"
        f"/prices - View current prices",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.message(Command("setwallet"))
async def cmd_setwallet(message: Message):
    """Set team wallet - owner only."""
    telegram_id = message.from_user.id
    
    if not is_owner(telegram_id):
        await message.answer("❌ This command is only for the bot owner.", parse_mode=None)
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "📝 <b>Usage:</b> /setwallet [wallet_address]\n\n"
            "Example:\n<code>/setwallet 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    new_wallet = args[1].strip()
    
    # Basic validation - Solana addresses are 32-44 base58 chars
    if len(new_wallet) < 32 or len(new_wallet) > 44:
        await message.answer("❌ Invalid wallet address format.", parse_mode=None)
        return
    
    await db.set_setting('team_wallet_address', new_wallet, telegram_id)
    
    await message.answer(
        f"✅ <b>Team Wallet Updated!</b>\n\n"
        f"New wallet address:\n<code>{new_wallet}</code>\n\n"
        f"All payments will now be verified against this wallet.",
        parse_mode=ParseMode.HTML
    )


@router.message(Command("showwallet"))
async def cmd_showwallet(message: Message):
    """Show current team wallet - owner only."""
    telegram_id = message.from_user.id
    
    if not is_owner(telegram_id):
        await message.answer("❌ This command is only for the bot owner.", parse_mode=None)
        return
    
    db_wallet = await db.get_team_wallet()
    env_wallet = os.environ.get('TEAM_WALLET_ADDRESS', '')
    
    current_wallet = db_wallet or env_wallet or 'Not configured'
    source = "Database (set via /setwallet)" if db_wallet else ("Environment variable" if env_wallet else "None")
    
    await message.answer(
        f"💰 <b>Team Wallet Info</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Current Wallet:</b>\n<code>{current_wallet}</code>\n\n"
        f"<b>Source:</b> {source}\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "admin_setwallet")
async def callback_admin_setwallet(callback: CallbackQuery):
    """Prompt to set wallet via command."""
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ Owner only", show_alert=True)
        return
    
    await callback.message.answer(
        "📝 <b>Set Team Wallet</b>\n\n"
        "Send the command:\n"
        "<code>/setwallet YOUR_WALLET_ADDRESS</code>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Show bot stats - owner only."""
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ Owner only", show_alert=True)
        return
    
    # Get some basic stats
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to Admin", callback_data="action_admin")]
    ])
    
    await callback.message.edit_text(
        "📊 <b>Bot Statistics</b>\n\n"
        "(Full stats coming soon)",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "action_admin")
async def callback_admin(callback: CallbackQuery):
    """Show admin panel via button."""
    telegram_id = callback.from_user.id
    
    if not is_owner(telegram_id):
        await callback.answer("❌ Owner only", show_alert=True)
        return
    
    current_wallet = await db.get_team_wallet() or os.environ.get('TEAM_WALLET_ADDRESS', 'Not set')
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Set Team Wallet", callback_data="admin_setwallet")],
        [InlineKeyboardButton(text="💵 Set Prices", callback_data="admin_setprices")],
        [InlineKeyboardButton(text="📊 View Stats", callback_data="admin_stats")],
    ])
    
    await callback.message.edit_text(
        f"🔐 <b>ADMIN PANEL</b> 🔐\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Owner ID: <code>{telegram_id}</code>\n"
        f"💰 Team Wallet:\n<code>{current_wallet}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Commands:</b>\n"
        f"/setwallet [address] - Set team wallet\n"
        f"/setprice [pkg] [price] - Set package price\n"
        f"/setgrowth [pkg] [cm] - Set package growth\n"
        f"/prices - View current prices",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "admin_setprices")
async def callback_admin_setprices(callback: CallbackQuery):
    """Show prices and how to change them - owner only."""
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ Owner only", show_alert=True)
        return
    
    packages = await get_all_packages()
    pkg_list = "\n".join([
        f"{pkg['emoji']} Package {num}: +{pkg['growth']}cm = <b>{pkg['price']:,}</b> FAPCOIN"
        for num, pkg in packages.items()
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to Admin", callback_data="action_admin")]
    ])
    
    await callback.message.edit_text(
        f"💵 <b>Package Prices</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{pkg_list}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>To change:</b>\n"
        f"Price: <code>/setprice [pkg] [price]</code>\n"
        f"Growth: <code>/setgrowth [pkg] [cm]</code>\n\n"
        f"Example: <code>/setprice 1 7500</code>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "action_grow")
async def callback_grow(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    chat_id = callback.message.chat.id
    
    await db.get_or_create_user(telegram_id, callback.from_user.username, callback.from_user.first_name)
    await db.get_or_create_user_chat(telegram_id, chat_id)
    
    can_grow = await db.can_grow_today(telegram_id, chat_id)
    if not can_grow:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏆 View Leaderboard", callback_data="action_top")],
            [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="action_menu")]
        ])
        await callback.message.edit_text(
            "⏰ <b>Already Grown Today!</b>\n\n"
            "Come back tomorrow for your next growth.\n\n"
            "💡 Tip: Try PvP battles to gain more length!",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await callback.answer("You already grew today!", show_alert=True)
        return
    
    growth = random.randint(-5, 20)
    old_length, new_length, actual_growth, bonus = await db.do_grow(telegram_id, chat_id, growth)
    
    name = callback.from_user.first_name or "Player"
    
    if growth < 0:
        emoji = "📉"
        result = f"<b>Ouch!</b> You shrunk by {abs(growth)} cm!"
        mood = "😢"
    elif growth == 0:
        emoji = "😐"
        result = "<b>No change today...</b>"
        mood = "🤷"
    elif growth < 10:
        emoji = "📈"
        result = f"<b>Nice!</b> You grew by {growth} cm!"
        mood = "😊"
    else:
        emoji = "🚀"
        result = f"<b>AMAZING!</b> You grew by {growth} cm!"
        mood = "🔥"
    
    bonus_text = f"\n🎁 Debt Bonus: +{bonus:.1f} cm" if bonus > 0 else ""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 View Leaderboard", callback_data="action_top")],
        [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="action_menu")]
    ])
    
    await callback.message.edit_text(
        f"{emoji} <b>DAILY GROWTH</b> {emoji}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{mood} {result}{bonus_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📏 <b>Your Total Length:</b> {new_length:.1f} cm\n\n"
        f"Come back tomorrow for more growth!",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer(f"You grew {growth} cm!")


@router.message(Command("grow"))
async def cmd_grow(message: Message):
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    await db.get_or_create_user_chat(telegram_id, chat_id)
    
    can_grow = await db.can_grow_today(telegram_id, chat_id)
    if not can_grow:
        await message.answer("⏰ You already grew today! Come back tomorrow.", parse_mode=None)
        return
    
    growth = random.randint(-5, 20)
    old_length, new_length, actual_growth, bonus = await db.do_grow(telegram_id, chat_id, growth)
    
    name = message.from_user.first_name or "Player"
    
    if growth < 0:
        emoji = "📉"
    elif growth == 0:
        emoji = "😐"
    else:
        emoji = "📈"
    
    bonus_text = f"\n🎁 Debt Bonus: +{bonus:.1f} cm" if bonus > 0 else ""
    
    await message.answer(
        f"{emoji} <b>{name}</b> {'shrunk' if growth < 0 else 'grew'} by <b>{abs(growth)}</b> cm!{bonus_text}\n\n"
        f"📏 Total: <b>{new_length:.1f}</b> cm",
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "action_top")
async def callback_top(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    leaderboard = await db.get_leaderboard(chat_id)
    
    if not leaderboard:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌱 Be the First to Grow!", callback_data="action_grow")],
            [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="action_menu")]
        ])
        await callback.message.edit_text(
            "🏆 <b>LEADERBOARD</b>\n\n"
            "No players yet!\n"
            "Be the first to grow and claim the top spot!",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    text = "🏆 <b>LEADERBOARD</b> 🏆\n\n━━━━━━━━━━━━━━━━━━━━━\n"
    
    for i, user in enumerate(leaderboard):
        name = user['first_name'] or user['username'] or f"Player"
        if user['username']:
            name = f"@{user['username']}"
        medal = medals[i] if i < len(medals) else f"{i+1}."
        text += f"{medal} {name}: <b>{user['total']:.1f}</b> cm\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_button(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(Command("top"))
async def cmd_top(message: Message):
    chat_id = message.chat.id
    leaderboard = await db.get_leaderboard(chat_id)
    
    if not leaderboard:
        await message.answer("🏆 No players yet! Use /grow to start.", parse_mode=None)
        return
    
    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 <b>LEADERBOARD</b> 🏆\n\n"
    
    for i, user in enumerate(leaderboard):
        name = user['first_name'] or user['username'] or f"Player"
        if user['username']:
            name = f"@{user['username']}"
        medal = medals[i] if i < len(medals) else f"{i+1}."
        text += f"{medal} {name}: <b>{user['total']:.1f}</b> cm\n"
    
    await message.answer(text, parse_mode=ParseMode.HTML)


@router.message(Command("daily"))
async def cmd_daily(message: Message):
    chat_id = message.chat.id
    
    has_winner = await db.has_daily_winner_today(chat_id)
    if has_winner:
        await message.answer(
            "🎲 <b>DICK OF THE DAY</b>\n\n"
            "Today's winner has already been selected!\n"
            "Come back tomorrow!",
            parse_mode=ParseMode.HTML
        )
        return
    
    winner = await db.select_daily_winner(chat_id)
    
    if not winner:
        await message.answer(
            "🎲 <b>DICK OF THE DAY</b>\n\n"
            "No eligible players! Use /grow first.",
            parse_mode=ParseMode.HTML
        )
        return
    
    name = winner['first_name'] or winner['username'] or "Player"
    if winner['username']:
        name = f"@{winner['username']}"
    
    await message.answer(
        f"🎲 <b>DICK OF THE DAY</b> 🎲\n\n"
        f"🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉\n\n"
        f"👑 <b>{name}</b> 👑\n\n"
        f"🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉\n\n"
        f"🎁 Bonus: <b>+{winner['bonus']} cm</b>!",
        parse_mode=ParseMode.HTML
    )


@router.message(Command("buy"))
async def cmd_buy(message: Message):
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    await db.get_or_create_user_chat(telegram_id, chat_id)
    
    # Check if custom amount specified: /buy 150
    args = message.text.split()
    if len(args) > 1:
        try:
            amount = int(args[1])
            if amount < 1:
                await message.answer("❌ Amount must be at least 1 cm", parse_mode=None)
                return
            if amount > MAX_BUY_AMOUNT:
                await message.answer(f"❌ Maximum purchase is {MAX_BUY_AMOUNT} cm per transaction", parse_mode=None)
                return
            
            await db.create_pending_transaction(telegram_id, chat_id, amount, amount)
            team_wallet = await db.get_team_wallet() or os.environ.get('TEAM_WALLET_ADDRESS', 'Not configured')
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ I've Paid!", callback_data=f"paid_{amount}")],
                [InlineKeyboardButton(text="◀️ Back", callback_data="action_buy")]
            ])
            
            await message.answer(
                f"💰 <b>BUY {amount} CM</b> 💰\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🌱 <b>+{amount} cm Growth</b>\n"
                f"💵 Price: <b>{amount:,} $FAPCOIN</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📤 <b>Send exactly {amount:,} FAPCOIN to:</b>\n\n"
                f"<code>{team_wallet}</code>\n\n"
                f"⬆️ <i>Tap to copy address</i>\n\n"
                f"After sending, click <b>I've Paid!</b>",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            return
        except ValueError:
            pass
    
    # Show buy menu
    await message.answer(
        "💰 <b>BUY GROWTH</b> 💰\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💎 <b>1 FAPCOIN = 1 cm</b>\n"
        "📦 Max per purchase: <b>10000 cm</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select amount or enter custom:",
        reply_markup=get_buy_keyboard(),
        parse_mode=ParseMode.HTML
    )


@router.message(Command("loan"))
async def cmd_loan(message: Message):
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    user_chat = await db.get_or_create_user_chat(telegram_id, chat_id)
    
    if user_chat.length >= 0:
        await message.answer(
            "💳 <b>LOAN SYSTEM</b>\n\n"
            f"Your length: <b>{user_chat.length:.1f}</b> cm\n"
            f"Debt: <b>{user_chat.debt:.1f}</b> cm\n\n"
            "You don't need a loan!",
            parse_mode=ParseMode.HTML
        )
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Accept Loan", callback_data="confirm_loan")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="action_menu")]
    ])
    
    debt_amount = abs(user_chat.length)
    
    await message.answer(
        f"💳 <b>LOAN OFFER</b> 💳\n\n"
        f"Your length: <b>{user_chat.length:.1f}</b> cm\n\n"
        f"We can reset to <b>0 cm</b>!\n\n"
        f"⚠️ Adds <b>{debt_amount:.1f} cm</b> debt.\n"
        f"📉 20% of growth goes to repayment.\n\n"
        f"Accept?",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "action_gift_info")
async def callback_gift_info(callback: CallbackQuery):
    await callback.message.edit_text(
        "💝 <b>GIFT CM</b> 💝\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Share your length with friends!\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>How to gift:</b>\n"
        "1. Go to the group chat\n"
        "2. Reply to someone's message\n"
        "3. Type: <code>/gift [amount]</code>\n\n"
        "<b>Example:</b>\n"
        "Reply to a message + <code>/gift 10</code>\n\n"
        "⚠️ Minimum gift: 1 cm\n"
        "⚠️ Gifts only work in groups!",
        reply_markup=get_back_button(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(Command("gift"))
async def cmd_gift(message: Message):
    """Gift cm to another user."""
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("❌ Gifts only work in groups!", parse_mode=None)
        return
    
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    
    # Check if replying to someone
    if not message.reply_to_message:
        await message.answer(
            "🎁 <b>GIFT CM</b> 🎁\n\n"
            "Reply to someone's message with:\n"
            "<code>/gift [amount]</code>\n\n"
            "Example: Reply + <code>/gift 10</code>\n"
            "to give them 10 cm!",
            parse_mode=ParseMode.HTML
        )
        return
    
    receiver = message.reply_to_message.from_user
    
    if receiver.is_bot:
        await message.answer("❌ Can't gift to bots!", parse_mode=None)
        return
    
    if receiver.id == telegram_id:
        await message.answer("❌ Can't gift to yourself!", parse_mode=None)
        return
    
    # Parse amount
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ Specify amount!\n\n"
            "Usage: <code>/gift [amount]</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        amount = float(args[1])
    except ValueError:
        await message.answer("❌ Invalid amount!", parse_mode=None)
        return
    
    if amount <= 0:
        await message.answer("❌ Amount must be positive!", parse_mode=None)
        return
    
    if amount < 1:
        await message.answer("❌ Minimum gift is 1 cm!", parse_mode=None)
        return
    
    # Ensure both users exist
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    await db.get_or_create_user(receiver.id, receiver.username, receiver.first_name)
    await db.get_or_create_user_chat(telegram_id, chat_id)
    await db.get_or_create_user_chat(receiver.id, chat_id)
    
    # Process gift
    result = await db.gift_length(telegram_id, receiver.id, chat_id, amount)
    
    if not result["success"]:
        if result["error"] == "insufficient_length":
            await message.answer(
                f"❌ <b>Not enough length!</b>\n\n"
                f"You have: <b>{result['available']:.1f}</b> cm\n"
                f"Trying to gift: <b>{amount:.1f}</b> cm",
                parse_mode=ParseMode.HTML
            )
        else:
            await message.answer("❌ Gift failed. Try again.", parse_mode=None)
        return
    
    sender_name = message.from_user.first_name or message.from_user.username or "Someone"
    receiver_name = receiver.first_name or receiver.username or "Someone"
    
    await message.answer(
        f"🎁 <b>GIFT SENT!</b> 🎁\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💝 <b>{sender_name}</b> gifted\n"
        f"🍆 <b>{amount:.1f} cm</b> to\n"
        f"🎉 <b>{receiver_name}</b>!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📏 Your new length: <b>{result['sender_new_total']:.1f}</b> cm\n"
        f"📏 Their new length: <b>{result['receiver_new_total']:.1f}</b> cm",
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "action_stats")
async def callback_stats(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    chat_id = callback.message.chat.id
    
    await db.get_or_create_user(telegram_id, callback.from_user.username, callback.from_user.first_name)
    user_chat = await db.get_or_create_user_chat(telegram_id, chat_id)
    
    total = user_chat.length + user_chat.paid_length
    
    # PvP stats
    wins = getattr(user_chat, 'pvp_wins', 0) or 0
    losses = getattr(user_chat, 'pvp_losses', 0) or 0
    streak = getattr(user_chat, 'pvp_streak', 0) or 0
    total_battles = wins + losses
    win_rate = (wins / total_battles * 100) if total_battles > 0 else 0
    
    # Streak display
    if streak > 0:
        streak_text = f"🔥 {streak}W"
    elif streak < 0:
        streak_text = f"❄️ {abs(streak)}L"
    else:
        streak_text = "—"
    
    await callback.message.edit_text(
        f"📊 <b>YOUR STATS</b> 📊\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📏 Free Growth: <b>{user_chat.length:.1f}</b> cm\n"
        f"💰 Paid Growth: <b>{user_chat.paid_length:.1f}</b> cm\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📐 <b>TOTAL: {total:.1f} cm</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚔️ <b>PVP RECORD</b>\n"
        f"🏆 Wins: <b>{wins}</b> | 💀 Losses: <b>{losses}</b>\n"
        f"📈 Win Rate: <b>{win_rate:.1f}%</b>\n"
        f"🔥 Streak: <b>{streak_text}</b>\n\n"
        f"💳 Debt: <b>{user_chat.debt:.1f}</b> cm",
        reply_markup=get_back_button(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "action_daily")
async def callback_daily(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    
    has_winner = await db.has_daily_winner_today(chat_id)
    if has_winner:
        await callback.message.edit_text(
            "🎲 <b>DICK OF THE DAY</b> 🎲\n\n"
            "Today's winner has already been selected!\n\n"
            "Come back tomorrow for the next drawing!",
            reply_markup=get_back_button(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer("Already selected today!", show_alert=True)
        return
    
    winner = await db.select_daily_winner(chat_id)
    
    if not winner:
        await callback.message.edit_text(
            "🎲 <b>DICK OF THE DAY</b> 🎲\n\n"
            "No eligible players!\n\n"
            "Players must use /grow at least once in the past 7 days to be eligible.",
            reply_markup=get_back_button(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer("No eligible players!", show_alert=True)
        return
    
    name = winner['first_name'] or winner['username'] or "Player"
    if winner['username']:
        name = f"@{winner['username']}"
    
    await callback.message.edit_text(
        f"🎲 <b>DICK OF THE DAY</b> 🎲\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉\n\n"
        f"👑 <b>{name}</b> 👑\n\n"
        f"🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎁 Bonus: <b>+{winner['bonus']} cm</b>!\n\n"
        f"Keep growing for your chance tomorrow!",
        reply_markup=get_back_button(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer(f"🎉 {name} wins!", show_alert=True)


@router.callback_query(F.data == "action_loan")
async def callback_loan(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    chat_id = callback.message.chat.id
    
    await db.get_or_create_user(telegram_id, callback.from_user.username, callback.from_user.first_name)
    await db.get_or_create_user_chat(telegram_id, chat_id)
    
    user_chat = await db.get_or_create_user_chat(telegram_id, chat_id)
    
    if user_chat.length >= 0:
        await callback.message.edit_text(
            "💳 <b>LOAN SYSTEM</b> 💳\n\n"
            f"Your current length: <b>{user_chat.length:.1f}</b> cm\n"
            f"Current debt: <b>{user_chat.debt:.1f}</b> cm\n\n"
            "You don't need a loan! Your length is positive.\n\n"
            "💡 Loans are for resetting negative length to zero.",
            reply_markup=get_back_button(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer("You don't need a loan!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Accept Loan", callback_data="confirm_loan")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="action_menu")]
    ])
    
    debt_amount = abs(user_chat.length)
    
    await callback.message.edit_text(
        f"💳 <b>LOAN OFFER</b> 💳\n\n"
        f"Your current length: <b>{user_chat.length:.1f}</b> cm\n\n"
        f"We can reset your length to <b>0 cm</b>!\n\n"
        f"⚠️ This will add <b>{debt_amount:.1f} cm</b> to your debt.\n"
        f"📉 20% of future growth goes to debt repayment.\n\n"
        f"Accept the loan?",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_loan")
async def callback_confirm_loan(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    chat_id = callback.message.chat.id
    
    success, new_length, debt = await db.apply_loan(telegram_id, chat_id)
    
    if success:
        await callback.message.edit_text(
            "✅ <b>LOAN APPROVED</b> ✅\n\n"
            f"Your length is now: <b>{new_length:.1f}</b> cm\n"
            f"Total debt: <b>{debt:.1f}</b> cm\n\n"
            "20% of your positive growth will repay the debt.",
            reply_markup=get_back_button(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer("Loan approved!")
    else:
        await callback.answer("Loan not needed - you have positive length!", show_alert=True)




@router.callback_query(F.data == "action_buy")
async def callback_buy(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    chat_id = callback.message.chat.id
    
    await db.get_or_create_user(telegram_id, callback.from_user.username, callback.from_user.first_name)
    await db.get_or_create_user_chat(telegram_id, chat_id)
    
    await callback.message.edit_text(
        "💰 <b>BUY GROWTH</b> 💰\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💎 <b>1 FAPCOIN = 1 cm</b>\n"
        "📦 Max per purchase: <b>10000 cm</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select amount or enter custom:",
        reply_markup=get_buy_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_amount_"))
async def callback_buy_amount(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    chat_id = callback.message.chat.id
    amount = int(callback.data.split("_")[2])
    
    if amount < 1 or amount > MAX_BUY_AMOUNT:
        await callback.answer(f"Invalid amount! Max is {MAX_BUY_AMOUNT} cm", show_alert=True)
        return
    
    await db.get_or_create_user(telegram_id, callback.from_user.username, callback.from_user.first_name)
    await db.get_or_create_user_chat(telegram_id, chat_id)
    await db.create_pending_transaction(telegram_id, chat_id, amount, amount)  # 1:1 ratio
    
    team_wallet = await db.get_team_wallet() or os.environ.get('TEAM_WALLET_ADDRESS', 'Not configured')
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ I've Paid!", callback_data=f"paid_{amount}")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="action_buy")]
    ])
    
    await callback.message.edit_text(
        f"💰 <b>BUY {amount} CM</b> 💰\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌱 <b>+{amount} cm Growth</b>\n"
        f"💵 Price: <b>{amount:,} $FAPCOIN</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📤 <b>Send exactly {amount:,} FAPCOIN to:</b>\n\n"
        f"<code>{team_wallet}</code>\n\n"
        f"⬆️ <i>Tap to copy address</i>\n\n"
        f"After sending, click <b>I've Paid!</b>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "buy_custom")
async def callback_buy_custom(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back", callback_data="action_buy")]
    ])
    
    await callback.message.edit_text(
        "📝 <b>CUSTOM AMOUNT</b> 📝\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💎 <b>1 FAPCOIN = 1 cm</b>\n"
        f"📦 Max: <b>{MAX_BUY_AMOUNT} cm</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Type the amount you want to buy:\n\n"
        "Example: <code>/buy 150</code>\n\n"
        "<i>This will cost 150 FAPCOIN for +150 cm</i>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("paid_"))
async def callback_paid(callback: CallbackQuery):
    amount = int(callback.data.split("_")[1])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back", callback_data="action_buy")]
    ])
    
    await callback.message.edit_text(
        f"📝 <b>VERIFY YOUR PAYMENT</b> 📝\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Amount: <b>+{amount} cm</b>\n"
        f"💵 Cost: <b>{amount:,} FAPCOIN</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 <b>Just paste your transaction hash below!</b>\n\n"
        f"💡 Find it in your wallet's transaction history\n"
        f"and send it here. I'll verify it automatically!",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(Command("verify"))
async def cmd_verify(message: Message):
    import logging
    logger = logging.getLogger(__name__)
    
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    args = message.text.split()
    
    logger.info(f"Verify command from user {telegram_id} in chat {chat_id}, args: {args}")
    
    await message.answer("⏳ Processing...", parse_mode=None)
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    
    if len(args) < 2:
        await message.answer(
            "📝 <b>VERIFY PAYMENT</b>\n\n"
            "Usage: /verify [transaction_hash]\n\n"
            "Paste your Solana transaction signature after /verify",
            parse_mode=ParseMode.HTML
        )
        return
    
    tx_hash = args[1].strip()
    
    if not validate_solana_tx_hash(tx_hash):
        await message.answer(
            "❌ <b>Invalid Transaction Hash</b>\n\n"
            "Please provide a valid Solana transaction signature.\n\n"
            "It should be 87-88 characters of base58 encoding.",
            parse_mode=ParseMode.HTML
        )
        return
    
    already_used = await db.is_transaction_already_used(tx_hash)
    if already_used:
        await message.answer(
            "❌ <b>Transaction Already Used</b>\n\n"
            "This transaction has already been claimed.",
            parse_mode=ParseMode.HTML
        )
        return
    
    pending_txs = await db.get_pending_transactions(telegram_id)
    logger.info(f"Found {len(pending_txs) if pending_txs else 0} pending transactions for user {telegram_id}")
    
    if not pending_txs:
        await message.answer(
            "❌ <b>No Pending Purchase</b>\n\n"
            "Use /buy or /menu to buy a package first.",
            parse_mode=ParseMode.HTML
        )
        return
    
    pending_tx = pending_txs[0]
    # package_number now stores the amount (1:1 ratio)
    growth_amount = pending_tx.package_number
    logger.info(f"Verifying tx {tx_hash[:20]}... for {growth_amount} cm")
    
    solana_rpc = os.environ.get('SOLANA_RPC_URL', '')
    team_wallet = await db.get_team_wallet() or os.environ.get('TEAM_WALLET_ADDRESS', '')
    
    if not solana_rpc or not team_wallet:
        await message.answer(
            "⚠️ <b>Verification Unavailable</b>\n\n"
            "Payment verification is not configured.\n"
            "Please contact support.",
            parse_mode=ParseMode.HTML
        )
        return
    
    await message.answer("🔍 <b>Verifying transaction on Solana...</b>", parse_mode=ParseMode.HTML)
    
    try:
        verification = await verify_solana_transaction(
            tx_hash, team_wallet, pending_tx.amount_paid, solana_rpc
        )
        
        if verification['verified']:
            success = await db.confirm_transaction(pending_tx.transaction_id, tx_hash, growth_amount)
            if success:
                await message.answer(
                    f"✅ <b>PAYMENT VERIFIED!</b> ✅\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎉 You received <b>+{growth_amount} cm</b>!\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"💎 Every purchase in $FAPCOIN is sent to our\n"
                    f"treasury wallet to support the project! 💎\n\n"
                    f"Thank you for your purchase!",
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.answer("❌ Error confirming. Contact support.", parse_mode=None)
        else:
            error = verification.get('error', 'unknown')
            if error == 'tx_not_found':
                error_msg = "Transaction not found. Wait a few minutes and try again."
            elif error == 'tx_failed':
                error_msg = "Transaction failed on blockchain."
            elif error == 'transfer_not_found':
                error_msg = "Transfer to team wallet not found in transaction."
            else:
                error_msg = "Could not verify transaction."
            
            await message.answer(
                f"❌ <b>Verification Failed</b>\n\n{error_msg}\n\n"
                f"If you believe this is an error, contact support.",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        import logging
        logging.error(f"Verification error: {e}")
        await message.answer(
            f"❌ <b>Error verifying transaction</b>\n\n"
            f"Please try again later or contact support.",
            parse_mode=ParseMode.HTML
        )


async def verify_solana_transaction(tx_hash: str, to_wallet: str, expected_amount: float, rpc_url: str) -> dict:
    result = {'verified': False, 'error': None, 'found_amount': 0, 'found_to': None}
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [tx_hash, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
            }
            
            async with session.post(rpc_url, json=payload) as response:
                if response.status != 200:
                    result['error'] = 'rpc_error'
                    return result
                
                data = await response.json()
                
                if 'result' not in data or data['result'] is None:
                    result['error'] = 'tx_not_found'
                    return result
                
                tx = data['result']
                
                if tx.get('meta', {}).get('err') is not None:
                    result['error'] = 'tx_failed'
                    return result
                
                instructions = tx.get('transaction', {}).get('message', {}).get('instructions', [])
                inner_instructions = tx.get('meta', {}).get('innerInstructions', [])
                
                all_instructions = list(instructions)
                for inner in inner_instructions:
                    all_instructions.extend(inner.get('instructions', []))
                
                for instr in all_instructions:
                    parsed = instr.get('parsed')
                    if not parsed:
                        continue
                    
                    instr_type = parsed.get('type', '')
                    info = parsed.get('info', {})
                    
                    if instr_type in ['transfer', 'transferChecked']:
                        destination = info.get('destination', '')
                        
                        if instr_type == 'transferChecked':
                            token_amount = info.get('tokenAmount', {})
                            amount = float(token_amount.get('uiAmount', 0))
                        else:
                            amount = float(info.get('amount', 0))
                            amount = amount / (10 ** 9)
                        
                        result['found_amount'] = amount
                        result['found_to'] = destination
                        
                        if to_wallet.lower() in destination.lower() or destination.lower() in to_wallet.lower():
                            if amount >= expected_amount * 0.99:
                                result['verified'] = True
                                return result
                
                post_balances = tx.get('meta', {}).get('postTokenBalances', [])
                pre_balances = tx.get('meta', {}).get('preTokenBalances', [])
                
                for post in post_balances:
                    owner = post.get('owner', '')
                    if owner.lower() == to_wallet.lower():
                        post_amount = float(post.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                        pre_amount = 0
                        for pre in pre_balances:
                            if pre.get('accountIndex') == post.get('accountIndex'):
                                pre_amount = float(pre.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                                break
                        
                        received = post_amount - pre_amount
                        if received >= expected_amount * 0.99:
                            result['verified'] = True
                            result['found_amount'] = received
                            result['found_to'] = owner
                            return result
                
                result['error'] = 'transfer_not_found'
                return result
                
    except Exception as e:
        result['error'] = f'exception'
        return result


@router.callback_query(F.data == "action_pvp_info")
async def callback_pvp_info(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚔️ <b>PVP BATTLES</b> ⚔️\n\n"
        "Challenge other players and bet your length!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 <b>How to Play:</b>\n"
        "1️⃣ Reply to someone's message\n"
        "2️⃣ Use: /pvp [bet amount]\n"
        "3️⃣ They accept or decline\n"
        "4️⃣ Winner takes the bet!\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Example: <code>/pvp 10</code>\n"
        "(Bet 10 cm on the battle)",
        reply_markup=get_back_button(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(Command("pvp"))
@router.message(F.text.regexp(r"@\w+\s+/pvp"))
async def cmd_pvp(message: Message):
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    await db.get_or_create_user_chat(telegram_id, chat_id)
    
    # Parse the command - support both reply and @mention formats
    # Format 1: Reply to message + /pvp [bet]
    # Format 2: @username /pvp [bet] or /pvp @username [bet]
    
    text = message.text or ""
    opponent = None
    bet = None
    
    # Check for mentions in the message
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                # Extract @username from text
                mention_text = text[entity.offset:entity.offset + entity.length]
                username = mention_text.lstrip("@")
                # Find user by username in database
                opponent_user = await db.get_user_by_username(username)
                if opponent_user:
                    opponent = opponent_user
                break
            elif entity.type == "text_mention" and entity.user:
                # Direct user mention (when user has no username)
                opponent = entity.user
                break
    
    # If no mention found, check for reply
    if not opponent and message.reply_to_message:
        opponent = message.reply_to_message.from_user
    
    # Parse bet amount from arguments
    args = text.split()
    for arg in args:
        if arg.startswith("/") or arg.startswith("@"):
            continue
        try:
            bet = float(arg)
            if bet > 0:
                break
        except ValueError:
            continue
    
    # Show help if no opponent or bet
    if not opponent:
        await message.answer(
            "⚔️ <b>PVP BATTLE</b>\n\n"
            "Challenge someone to battle!\n\n"
            "<b>Option 1:</b> Tag opponent\n"
            "<code>@username /pvp 5</code>\n\n"
            "<b>Option 2:</b> Reply to their message\n"
            "Reply + <code>/pvp 5</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    if not bet or bet <= 0:
        await message.answer("❌ Please specify a bet amount. Example: <code>@user /pvp 5</code>", parse_mode=ParseMode.HTML)
        return
    
    # Handle opponent as either User object or database user
    if hasattr(opponent, 'id'):
        opponent_id = opponent.id
        opponent_username = getattr(opponent, 'username', None)
        opponent_first_name = getattr(opponent, 'first_name', None) or "Player"
        is_bot = getattr(opponent, 'is_bot', False)
    else:
        opponent_id = opponent.telegram_id
        opponent_username = opponent.username
        opponent_first_name = opponent.first_name or "Player"
        is_bot = False
    
    if opponent_id == telegram_id:
        await message.answer("❌ You can't battle yourself!", parse_mode=None)
        return
    
    if is_bot:
        await message.answer("❌ You can't battle bots!", parse_mode=None)
        return
    
    total = await db.get_total_length(telegram_id, chat_id)
    if total < bet:
        await message.answer(
            f"❌ <b>Insufficient Length</b>\n\n"
            f"You have: {total:.1f} cm\n"
            f"Bet required: {bet:.1f} cm",
            parse_mode=ParseMode.HTML
        )
        return
    
    await db.get_or_create_user(opponent_id, opponent_username, opponent_first_name)
    await db.get_or_create_user_chat(opponent_id, chat_id)
    
    challenge = await db.create_pvp_challenge(chat_id, telegram_id, opponent_id, bet, opponent_username)
    
    if not challenge:
        await message.answer("❌ Could not create challenge. Not enough length for that bet!", parse_mode=None)
        return
    
    challenger_name = message.from_user.first_name or "Player"
    opponent_name = opponent_first_name
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚔️ ACCEPT", callback_data=f"pvp_accept_{challenge.id}"),
            InlineKeyboardButton(text="🏃 DECLINE", callback_data=f"pvp_decline_{challenge.id}")
        ]
    ])
    
    # Tag opponent directly if they have username
    if opponent_username:
        opponent_tag = f"@{opponent_username}"
    else:
        opponent_tag = f"<a href='tg://user?id={opponent_id}'>{opponent_name}</a>"
    
    await message.answer(
        f"⚔️ <b>PVP CHALLENGE!</b> ⚔️\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔵 <b>{challenger_name}</b>\n"
        f"       ⚔️ VS ⚔️\n"
        f"🔴 <b>{opponent_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Bet: <b>{bet:.1f} cm</b>\n\n"
        f"{opponent_tag}, do you accept?",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("pvp_accept_"))
async def pvp_accept_callback(callback: CallbackQuery):
    challenge_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user_username = callback.from_user.username
    
    challenge = await db.get_pending_pvp_challenge(challenge_id)
    
    if not challenge:
        await callback.answer("Challenge expired!", show_alert=True)
        return
    
    # Allow accept if ID matches OR if username matches (for @mention challenges)
    id_match = (user_id == challenge.opponent_id)
    username_match = False
    try:
        username_match = (
            hasattr(challenge, 'opponent_username') and
            challenge.opponent_username and 
            user_username and 
            user_username.lower() == challenge.opponent_username.lower()
        )
    except Exception:
        pass
    
    if not id_match and not username_match:
        await callback.answer("This challenge is not for you!", show_alert=True)
        return
    
    # Update opponent_id to the actual user who accepted (in case it was wrong)
    if not id_match and username_match:
        try:
            await db.update_pvp_opponent_id(challenge_id, user_id)
        except Exception:
            pass
    
    result = await db.accept_pvp_challenge(challenge_id)
    
    if not result:
        await callback.answer("Error!", show_alert=True)
        return
    
    if result.get('error') == 'insufficient_funds':
        await callback.answer("You don't have enough length!", show_alert=True)
        return
    
    if result.get('error') == 'challenger_insufficient_funds':
        await callback.answer("Challenger no longer has enough length!", show_alert=True)
        return
    
    challenger_user = await db.get_user_by_telegram_id(result['challenger_id'])
    opponent_user = await db.get_user_by_telegram_id(result['opponent_id'])
    
    challenger_name = challenger_user.first_name if challenger_user else "Player 1"
    opponent_name = opponent_user.first_name if opponent_user else "Player 2"
    
    if result.get('draw'):
        await callback.message.edit_text(
            f"⚔️ <b>PVP RESULT</b> ⚔️\n\n"
            f"🎲 {challenger_name}: <b>{result['challenger_roll']}</b>\n"
            f"🎲 {opponent_name}: <b>{result['opponent_roll']}</b>\n\n"
            f"🤝 <b>IT'S A DRAW!</b>\n\n"
            f"No length exchanged.",
            parse_mode=ParseMode.HTML
        )
        await callback.answer("It's a draw!")
        return
    
    winner_user = await db.get_user_by_telegram_id(result['winner_id'])
    winner_name = winner_user.first_name if winner_user else "Winner"
    
    # Get current lengths for display
    winner_length = await db.get_total_length(result['winner_id'], challenge.chat_id)
    loser_length = await db.get_total_length(result['loser_id'], challenge.chat_id)
    
    loser_user = await db.get_user_by_telegram_id(result['loser_id'])
    loser_name = loser_user.first_name if loser_user else "Loser"
    
    # Get streak info
    winner_streak = result.get('winner_streak', 0)
    streak_line = f"🔥 <b>{winner_streak} Win Streak!</b>\n" if winner_streak > 1 else ""
    
    await callback.message.edit_text(
        f"⚔️ <b>PVP RESULT</b> ⚔️\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎲 <b>DICE ROLLS:</b>\n"
        f"{challenger_name}: {result['challenger_roll']}\n"
        f"{opponent_name}: {result['opponent_roll']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 <b>{winner_name} WINS!</b> 🏆\n"
        f"{streak_line}\n"
        f"📊 <b>RESULTS:</b>\n"
        f"✅ {winner_name}: +{result['bet']:.1f} cm → {winner_length:.1f} cm\n"
        f"❌ {loser_name}: -{result['bet']:.1f} cm → {loser_length:.1f} cm",
        parse_mode=ParseMode.HTML
    )
    await callback.answer(f"🏆 {winner_name} wins!")


@router.callback_query(F.data.startswith("pvp_decline_"))
async def pvp_decline_callback(callback: CallbackQuery):
    challenge_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user_username = callback.from_user.username
    
    challenge = await db.get_pending_pvp_challenge(challenge_id)
    
    if not challenge:
        await callback.answer("Challenge expired!", show_alert=True)
        return
    
    # Allow decline if ID matches OR if username matches (for @mention challenges)
    id_match = (user_id == challenge.opponent_id)
    username_match = False
    try:
        username_match = (
            hasattr(challenge, 'opponent_username') and
            challenge.opponent_username and 
            user_username and 
            user_username.lower() == challenge.opponent_username.lower()
        )
    except Exception:
        pass
    
    if not id_match and not username_match:
        await callback.answer("This challenge is not for you!", show_alert=True)
        return
    
    await db.decline_pvp_challenge(challenge_id)
    
    await callback.message.edit_text(
        "⚔️ <b>CHALLENGE DECLINED</b> ⚔️\n\n"
        "🏃 The opponent ran away!",
        parse_mode=ParseMode.HTML
    )
    await callback.answer("Challenge declined!")


@router.callback_query(F.data == "action_help")
async def callback_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "❓ <b>HELP & COMMANDS</b> ❓\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🎮 <b>GAMEPLAY</b>\n"
        "/grow - Daily growth (-5 to +20 cm)\n"
        "/top - Leaderboard\n"
        "/daily - Dick of the Day\n"
        "/pvp - Challenge players\n"
        "/loan - Borrow to reset debt\n\n"
        "💰 <b>PURCHASES</b>\n"
        "/buy - Buy growth with FAPCOIN\n"
        "/verify - Verify payment\n\n"
        "📱 <b>OTHER</b>\n"
        "/menu - Main menu\n"
        "/support - Get help\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=get_back_button(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "action_support")
async def callback_support(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Join Our TG", url="https://t.me/FapcoinByShitoshi")],
        [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="action_menu")]
    ])
    
    await callback.message.edit_text(
        "🆘 <b>SUPPORT</b> 🆘\n\n"
        "https://t.me/FapcoinByShitoshi\n\n"
        "Need help? Contact our support by joining our TG and tagging:\n\n"
        "👤 @boosteryting\n\n"
        "Click the button below to join our TG:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(Command("support"))
async def cmd_support(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Join Our TG", url="https://t.me/FapcoinByShitoshi")]
    ])
    
    await message.answer(
        "🆘 <b>SUPPORT</b> 🆘\n\n"
        "https://t.me/FapcoinByShitoshi\n\n"
        "Need help? Contact our support by joining our TG and tagging:\n\n"
        "👤 @boosteryting\n\n"
        "Click the button below to join our TG:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ <b>COMMANDS</b>\n\n"
        "/menu - Main menu\n"
        "/grow - Daily growth\n"
        "/top - Leaderboard\n"
        "/pvp - PvP battle\n"
        "/gift - Gift cm to someone\n"
        "/buy - Buy growth\n"
        "/verify - Verify payment\n"
        "/about - About this bot\n"
        "/support - Get help",
        parse_mode=ParseMode.HTML
    )


@router.message(Command("about"))
async def cmd_about(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Start Playing!", callback_data="action_menu")]
    ])
    
    await message.answer(
        "🍆 <b>FAPCOIN DICK BOT</b> 🍆\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "<b>The Ultimate Growth Game!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Welcome to the most fun and competitive\n"
        "growth game on Telegram!\n\n"
        "🌱 <b>DAILY GROWTH</b>\n"
        "Grow every day! Will you gain or shrink?\n"
        "It's a gamble every time! (-5 to +20 cm)\n\n"
        "⚔️ <b>PVP BATTLES</b>\n"
        "Challenge friends to battles!\n"
        "Both players roll dice (1-100)\n"
        "Higher roll wins the bet amount!\n\n"
        "<b>How to battle:</b>\n"
        "• Tag: <code>@username /pvp 5</code>\n"
        "• Reply: Reply to message + <code>/pvp 5</code>\n\n"
        "🏆 <b>LEADERBOARDS</b>\n"
        "Compete to be the biggest in your group!\n"
        "Check /top to see who's winning!\n\n"
        "🎁 <b>GIFTING</b>\n"
        "Send cm to your friends!\n"
        "Reply to someone + <code>/gift 10</code>\n\n"
        "💰 <b>BUY GROWTH</b>\n"
        "Skip the grind! Buy instant growth\n"
        "with <b>$FAPCOIN</b> on Solana!\n\n"
        "🎲 <b>DICK OF THE DAY</b>\n"
        "Daily lottery! Random player gets\n"
        "bonus growth every day at 12:00 UTC!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💎 Powered by <b>$FAPCOIN</b> on Solana\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.inline_query()
async def inline_handler(inline_query: InlineQuery):
    results = [
        InlineQueryResultArticle(
            id="grow", title="🌱 Grow", description="Daily growth",
            input_message_content=InputTextMessageContent(message_text="/grow")
        ),
        InlineQueryResultArticle(
            id="top", title="🏆 Leaderboard", description="View rankings",
            input_message_content=InputTextMessageContent(message_text="/top")
        ),
        InlineQueryResultArticle(
            id="menu", title="📱 Menu", description="Open main menu",
            input_message_content=InputTextMessageContent(message_text="/menu")
        ),
    ]
    await inline_query.answer(results, cache_time=60)


def extract_tx_hash(text: str) -> str | None:
    """Extract transaction hash from any format - URL, raw hash, or text containing hash."""
    text = text.strip()
    
    # Common Solana explorer URL patterns
    url_patterns = [
        r'solscan\.io/tx/([A-Za-z0-9]{43,90})',
        r'explorer\.solana\.com/tx/([A-Za-z0-9]{43,90})',
        r'solana\.fm/tx/([A-Za-z0-9]{43,90})',
        r'solanabeach\.io/transaction/([A-Za-z0-9]{43,90})',
    ]
    
    for pattern in url_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    # If it's a raw hash (direct paste)
    if validate_solana_tx_hash(text):
        return text
    
    # Try to find any base58 string that looks like a tx hash in the text
    # Solana tx hashes are 64-88 chars of base58 (typically 87-88)
    base58_pattern = r'\b([1-9A-HJ-NP-Za-km-z]{64,90})\b'
    matches = re.findall(base58_pattern, text)
    
    for match in matches:
        if validate_solana_tx_hash(match):
            return match
    
    return None


@router.message(F.text)
async def catch_tx_hash(message: Message):
    import logging
    logger = logging.getLogger(__name__)
    
    text = message.text.strip() if message.text else ""
    
    if text.startswith("/"):
        return
    
    logger.info(f"Received message from {message.from_user.id}: '{text[:50]}...'")
    
    # Try to extract tx hash from URL or raw text
    tx_hash = extract_tx_hash(text)
    
    if tx_hash:
        logger.info(f"Detected tx hash from user {message.from_user.id}: {tx_hash[:20]}...")
        
        telegram_id = message.from_user.id
        
        await message.answer(
            "🔍 <b>Transaction hash detected!</b>\n\n"
            "⏳ Checking Solana blockchain...",
            parse_mode=ParseMode.HTML
        )
        
        await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
        
        already_used = await db.is_transaction_already_used(tx_hash)
        if already_used:
            await message.answer(
                "❌ <b>Transaction Already Used</b>\n\n"
                "This transaction has already been claimed.",
                parse_mode=ParseMode.HTML
            )
            return
        
        pending_txs = await db.get_pending_transactions(telegram_id)
        if not pending_txs:
            await message.answer(
                "❌ <b>No Pending Purchase</b>\n\n"
                "Use /buy or /menu to select a package first.",
                parse_mode=ParseMode.HTML
            )
            return
        
        pending_tx = pending_txs[0]
        # package_number now stores the amount (1:1 ratio)
        growth_amount = pending_tx.package_number
        
        solana_rpc = os.environ.get('SOLANA_RPC_URL', '')
        team_wallet = await db.get_team_wallet() or os.environ.get('TEAM_WALLET_ADDRESS', '')
        
        if not solana_rpc or not team_wallet:
            await message.answer(
                "⚠️ <b>Verification Unavailable</b>\n\n"
                "Payment verification is not configured.\n"
                "Please contact support.",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            verification = await verify_solana_transaction(
                tx_hash, team_wallet, pending_tx.amount_paid, solana_rpc
            )
            
            if verification['verified']:
                success = await db.confirm_transaction(pending_tx.transaction_id, tx_hash, growth_amount)
                if success:
                    await message.answer(
                        f"✅ <b>PAYMENT VERIFIED!</b> ✅\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"✓ Transaction confirmed on Solana\n"
                        f"✓ Payment received: <b>{growth_amount:,} FAPCOIN</b>\n"
                        f"✓ Growth added to your account\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"🎉 <b>+{growth_amount} cm added!</b>\n\n"
                        f"💎 Every purchase in $FAPCOIN is sent to our\n"
                        f"treasury wallet to support the project! 💎\n\n"
                        f"Go back to the group and use /top to see\n"
                        f"your new position on the leaderboard!",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await message.answer("❌ Error confirming. Contact support.", parse_mode=None)
            else:
                error = verification.get('error', 'unknown')
                if error == 'tx_not_found':
                    error_msg = "Transaction not found. Wait a few minutes and try again."
                elif error == 'tx_failed':
                    error_msg = "Transaction failed on blockchain."
                elif error == 'transfer_not_found':
                    error_msg = "Transfer to team wallet not found in transaction."
                else:
                    error_msg = "Could not verify transaction."
                
                await message.answer(
                    f"❌ <b>Verification Failed</b>\n\n{error_msg}\n\n"
                    f"If you believe this is an error, contact support.",
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Verification error: {e}")
            await message.answer(
                "❌ <b>Error verifying transaction</b>\n\n"
                "Please try again later or contact support.",
                parse_mode=ParseMode.HTML
            )
