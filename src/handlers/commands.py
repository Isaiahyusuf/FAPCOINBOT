import os
import random
import re
import aiohttp
import base58
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.filters import Command, CommandStart, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.enums import ParseMode, ChatType

from src.database import db

router = Router()

PACKAGES = {
    1: {"growth": 20, "price": 5000, "emoji": "🌱"},
    2: {"growth": 40, "price": 10000, "emoji": "🌿"},
    3: {"growth": 60, "price": 15000, "emoji": "🌳"},
    4: {"growth": 80, "price": 20000, "emoji": "🚀"},
    5: {"growth": 100, "price": 25000, "emoji": "👑"},
}


def get_main_menu_keyboard():
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
            InlineKeyboardButton(text="💰 Buy Growth", callback_data="action_buy"),
            InlineKeyboardButton(text="👛 My Wallet", callback_data="action_wallet")
        ],
        [
            InlineKeyboardButton(text="📊 My Stats", callback_data="action_stats"),
            InlineKeyboardButton(text="💳 Loan", callback_data="action_loan")
        ],
        [
            InlineKeyboardButton(text="❓ Help", callback_data="action_help"),
            InlineKeyboardButton(text="🆘 Support", callback_data="action_support")
        ]
    ])


def get_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="action_menu")]
    ])


def get_packages_keyboard():
    buttons = []
    for num, pkg in PACKAGES.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{pkg['emoji']} Package {num}: +{pkg['growth']}cm for {pkg['price']:,} FAPCOIN",
                callback_data=f"buy_package_{num}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Back to Menu", callback_data="action_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def validate_solana_tx_hash(tx_hash: str) -> bool:
    if len(tx_hash) < 86 or len(tx_hash) > 90:
        return False
    try:
        decoded = base58.b58decode(tx_hash)
        if len(decoded) != 64:
            return False
        return True
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


@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    name = message.from_user.first_name or "Player"
    
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
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer(
        "🎮 <b>Main Menu</b>\n\n"
        "Select an option:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "action_menu")
async def callback_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎮 <b>Main Menu</b>\n\n"
        "Select an option:",
        reply_markup=get_main_menu_keyboard(),
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
    
    wallet = await db.get_wallet(telegram_id)
    if not wallet:
        await message.answer(
            "💰 <b>BUY GROWTH</b>\n\n"
            "⚠️ Register your wallet first!\n"
            "Use: /wallet YourSolanaAddress",
            parse_mode=ParseMode.HTML
        )
        return
    
    await message.answer(
        "💰 <b>GROWTH PACKAGES</b> 💰\n\n"
        "Select a package to purchase:",
        reply_markup=get_packages_keyboard(),
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


@router.callback_query(F.data == "action_stats")
async def callback_stats(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    chat_id = callback.message.chat.id
    
    await db.get_or_create_user(telegram_id, callback.from_user.username, callback.from_user.first_name)
    user_chat = await db.get_or_create_user_chat(telegram_id, chat_id)
    wallet = await db.get_wallet(telegram_id)
    
    total = user_chat.length + user_chat.paid_length
    
    wallet_text = f"👛 Wallet: <code>{wallet[:8]}...{wallet[-8:]}</code>" if wallet else "👛 Wallet: Not registered"
    
    await callback.message.edit_text(
        f"📊 <b>YOUR STATS</b> 📊\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📏 Free Growth: <b>{user_chat.length:.1f}</b> cm\n"
        f"💰 Paid Growth: <b>{user_chat.paid_length:.1f}</b> cm\n"
        f"📐 <b>TOTAL: {total:.1f} cm</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 Debt: <b>{user_chat.debt:.1f}</b> cm\n"
        f"{wallet_text}",
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


@router.callback_query(F.data == "action_wallet")
async def callback_wallet(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    
    await db.get_or_create_user(telegram_id, callback.from_user.username, callback.from_user.first_name)
    wallet = await db.get_wallet(telegram_id)
    
    if wallet:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Update Wallet", callback_data="update_wallet")],
            [InlineKeyboardButton(text="💰 Buy Growth", callback_data="action_buy")],
            [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="action_menu")]
        ])
        await callback.message.edit_text(
            "👛 <b>YOUR WALLET</b> 👛\n\n"
            f"<code>{wallet}</code>\n\n"
            "✅ Wallet registered! You can now buy growth packages.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Register Wallet", callback_data="update_wallet")],
            [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="action_menu")]
        ])
        await callback.message.edit_text(
            "👛 <b>WALLET REGISTRATION</b> 👛\n\n"
            "No wallet registered yet.\n\n"
            "To buy growth packages with $FAPCOIN, you need to register your Solana wallet.\n\n"
            "Send your wallet address using:\n"
            "<code>/wallet YourSolanaAddress</code>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    await callback.answer()


@router.message(Command("wallet"))
async def cmd_wallet(message: Message):
    telegram_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    
    if len(args) < 2:
        wallet = await db.get_wallet(telegram_id)
        if wallet:
            await message.answer(
                f"👛 <b>Your Wallet</b>\n\n<code>{wallet}</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            await message.answer(
                "👛 No wallet registered.\n\n"
                "Usage: /wallet YourSolanaAddress",
                parse_mode=None
            )
        return
    
    wallet_address = args[1].strip()
    
    if not validate_solana_address(wallet_address):
        await message.answer(
            "❌ <b>Invalid Wallet Address</b>\n\n"
            "Please provide a valid Solana wallet address.",
            parse_mode=ParseMode.HTML
        )
        return
    
    await db.set_wallet(telegram_id, wallet_address)
    await message.answer(
        f"✅ <b>Wallet Registered!</b>\n\n"
        f"<code>{wallet_address}</code>\n\n"
        f"You can now buy growth packages!",
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "action_buy")
async def callback_buy(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    
    wallet = await db.get_wallet(telegram_id)
    if not wallet:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Register Wallet First", callback_data="action_wallet")],
            [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="action_menu")]
        ])
        await callback.message.edit_text(
            "💰 <b>BUY GROWTH</b> 💰\n\n"
            "⚠️ You need to register your Solana wallet first!\n\n"
            "Click below to register:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await callback.answer("Register wallet first!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 <b>GROWTH PACKAGES</b> 💰\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Select a package to purchase:\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=get_packages_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_package_"))
async def callback_buy_package(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    chat_id = callback.message.chat.id
    package_num = int(callback.data.split("_")[2])
    
    pkg = PACKAGES.get(package_num)
    if not pkg:
        await callback.answer("Invalid package!", show_alert=True)
        return
    
    wallet = await db.get_wallet(telegram_id)
    if not wallet:
        await callback.answer("Register wallet first!", show_alert=True)
        return
    
    await db.get_or_create_user_chat(telegram_id, chat_id)
    await db.create_pending_transaction(telegram_id, chat_id, package_num, pkg['price'])
    
    team_wallet = os.environ.get('TEAM_WALLET_ADDRESS', 'Not configured')
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ I've Sent Payment", callback_data=f"verify_prompt_{package_num}")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="action_buy")]
    ])
    
    await callback.message.edit_text(
        f"💰 <b>PURCHASE PACKAGE {package_num}</b> 💰\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{pkg['emoji']} <b>+{pkg['growth']} cm Growth</b>\n"
        f"💵 Price: <b>{pkg['price']:,} $FAPCOIN</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📤 Send exactly <b>{pkg['price']:,}</b> FAPCOIN to:\n\n"
        f"<code>{team_wallet}</code>\n\n"
        f"After sending, click the button below!",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("verify_prompt_"))
async def callback_verify_prompt(callback: CallbackQuery):
    package_num = int(callback.data.split("_")[2])
    
    await callback.message.edit_text(
        "📝 <b>VERIFY PAYMENT</b> 📝\n\n"
        "Please send the Solana transaction hash:\n\n"
        "<code>/verify YOUR_TX_HASH</code>\n\n"
        "You can find this in your wallet's transaction history.",
        reply_markup=get_back_button(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(Command("verify"))
async def cmd_verify(message: Message):
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    args = message.text.split()
    
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
    if not pending_txs:
        await message.answer(
            "❌ <b>No Pending Purchase</b>\n\n"
            "Use /menu to buy a package first.",
            parse_mode=ParseMode.HTML
        )
        return
    
    pending_tx = pending_txs[0]
    pkg = PACKAGES.get(pending_tx.package_number)
    
    if not pkg:
        await message.answer("❌ Invalid package.", parse_mode=None)
        return
    
    solana_rpc = os.environ.get('SOLANA_RPC_URL', '')
    team_wallet = os.environ.get('TEAM_WALLET_ADDRESS', '')
    user_wallet = await db.get_wallet(telegram_id)
    
    if not solana_rpc or not team_wallet:
        await message.answer(
            "⚠️ <b>Verification Unavailable</b>\n\n"
            "Payment verification is not configured.\n"
            "Please contact support.",
            parse_mode=ParseMode.HTML
        )
        return
    
    await message.answer("🔍 <b>Verifying transaction...</b>", parse_mode=ParseMode.HTML)
    
    try:
        verification = await verify_solana_transaction(
            tx_hash, user_wallet, team_wallet, pending_tx.amount_paid, solana_rpc
        )
        
        if verification['verified']:
            success = await db.confirm_transaction(pending_tx.transaction_id, tx_hash, pkg['growth'])
            if success:
                await message.answer(
                    f"✅ <b>PAYMENT VERIFIED!</b> ✅\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎉 You received <b>+{pkg['growth']} cm</b>!\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n\n"
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
        await message.answer("❌ Error verifying. Try again later.", parse_mode=None)


async def verify_solana_transaction(tx_hash: str, from_wallet: str, to_wallet: str, expected_amount: float, rpc_url: str) -> dict:
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
async def cmd_pvp(message: Message):
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    args = message.text.split()
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    await db.get_or_create_user_chat(telegram_id, chat_id)
    
    if not message.reply_to_message:
        await message.answer(
            "⚔️ <b>PVP BATTLE</b>\n\n"
            "Reply to someone's message and use:\n"
            "<code>/pvp [bet]</code>\n\n"
            "Example: Reply to a message, then send <code>/pvp 10</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    if len(args) < 2:
        await message.answer("Usage: Reply to a message + /pvp [bet_amount]", parse_mode=None)
        return
    
    try:
        bet = float(args[1])
        if bet <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid bet. Use a positive number.", parse_mode=None)
        return
    
    opponent = message.reply_to_message.from_user
    if opponent.id == telegram_id:
        await message.answer("❌ You can't battle yourself!", parse_mode=None)
        return
    
    if opponent.is_bot:
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
    
    await db.get_or_create_user(opponent.id, opponent.username, opponent.first_name)
    await db.get_or_create_user_chat(opponent.id, chat_id)
    
    challenge = await db.create_pvp_challenge(chat_id, telegram_id, opponent.id, bet)
    
    if not challenge:
        await message.answer("❌ Could not create challenge. You may have a pending challenge.", parse_mode=None)
        return
    
    challenger_name = message.from_user.first_name or "Player"
    opponent_name = opponent.first_name or "Player"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚔️ ACCEPT", callback_data=f"pvp_accept_{challenge.id}"),
            InlineKeyboardButton(text="🏃 DECLINE", callback_data=f"pvp_decline_{challenge.id}")
        ]
    ])
    
    await message.answer(
        f"⚔️ <b>PVP CHALLENGE!</b> ⚔️\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔵 <b>{challenger_name}</b>\n"
        f"       ⚔️ VS ⚔️\n"
        f"🔴 <b>{opponent_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Bet: <b>{bet:.1f} cm</b>\n\n"
        f"<b>{opponent_name}</b>, do you accept?",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("pvp_accept_"))
async def pvp_accept_callback(callback: CallbackQuery):
    challenge_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    challenge = await db.get_pending_pvp_challenge(challenge_id)
    
    if not challenge:
        await callback.answer("Challenge expired!", show_alert=True)
        return
    
    if user_id != challenge.opponent_id:
        await callback.answer("This challenge is not for you!", show_alert=True)
        return
    
    result = await db.accept_pvp_challenge(challenge_id)
    
    if not result:
        await callback.answer("Error!", show_alert=True)
        return
    
    if result.get('error') == 'insufficient_funds':
        await callback.answer("You don't have enough length!", show_alert=True)
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
    
    await callback.message.edit_text(
        f"⚔️ <b>PVP RESULT</b> ⚔️\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎲 {challenger_name}: <b>{result['challenger_roll']}</b>\n"
        f"🎲 {opponent_name}: <b>{result['opponent_roll']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 <b>{winner_name} WINS!</b> 🏆\n\n"
        f"💰 +{result['bet']:.1f} cm",
        parse_mode=ParseMode.HTML
    )
    await callback.answer(f"🏆 {winner_name} wins!")


@router.callback_query(F.data.startswith("pvp_decline_"))
async def pvp_decline_callback(callback: CallbackQuery):
    challenge_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    challenge = await db.get_pending_pvp_challenge(challenge_id)
    
    if not challenge:
        await callback.answer("Challenge expired!", show_alert=True)
        return
    
    if user_id != challenge.opponent_id:
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
        "/wallet - Register Solana wallet\n"
        "/buy - View packages\n"
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
    support_username = os.environ.get('SUPPORT_USERNAME', '')
    
    if support_username:
        if not support_username.startswith('@'):
            support_username = '@' + support_username
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Contact Support", url=f"https://t.me/{support_username.lstrip('@')}")],
            [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="action_menu")]
        ])
        
        await callback.message.edit_text(
            "🆘 <b>SUPPORT</b> 🆘\n\n"
            f"Need help? Contact our support:\n\n"
            f"👤 {support_username}\n\n"
            "Click the button below to start a chat:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.edit_text(
            "🆘 <b>SUPPORT</b> 🆘\n\n"
            "Support is not configured.\n\n"
            "Please try again later.",
            reply_markup=get_back_button(),
            parse_mode=ParseMode.HTML
        )
    await callback.answer()


@router.message(Command("support"))
async def cmd_support(message: Message):
    support_username = os.environ.get('SUPPORT_USERNAME', '')
    
    if support_username:
        if not support_username.startswith('@'):
            support_username = '@' + support_username
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Contact Support", url=f"https://t.me/{support_username.lstrip('@')}")]
        ])
        
        await message.answer(
            f"🆘 <b>SUPPORT</b>\n\n"
            f"Contact: {support_username}",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer("Support not configured.", parse_mode=None)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ <b>COMMANDS</b>\n\n"
        "/menu - Main menu\n"
        "/grow - Daily growth\n"
        "/top - Leaderboard\n"
        "/pvp - PvP battle\n"
        "/wallet - Set wallet\n"
        "/verify - Verify payment\n"
        "/support - Get help",
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
