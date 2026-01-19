import os
import random
import re
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode

from src.database import db

router = Router()

PACKAGES = {
    1: {"growth": 20, "price": 5000},
    2: {"growth": 40, "price": 10000},
    3: {"growth": 60, "price": 15000},
    4: {"growth": 80, "price": 20000},
    5: {"growth": 100, "price": 25000},
}


@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    await message.answer(
        "Welcome to FAPCOIN DICK BOT!\n\n"
        "Commands:\n"
        "/grow - Daily random growth (-5 to +20 cm)\n"
        "/top - Show chat leaderboard\n"
        "/pvp @user <bet> - Challenge a user\n"
        "/loan - Reset debt to zero\n"
        "/wallet <address> - Register Solana wallet\n"
        "/buy <package> - Purchase growth with $FAPCOIN\n"
        "/support - Request support\n\n"
        "Grow your length and compete with others!"
    )


@router.message(Command("grow"))
async def cmd_grow(message: Message):
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    
    await db.get_or_create_user(
        telegram_id,
        message.from_user.username,
        message.from_user.first_name
    )
    await db.get_or_create_user_chat(telegram_id, chat_id)
    
    can_grow = await db.can_grow_today(telegram_id, chat_id)
    if not can_grow:
        await message.answer("You already grew today! Come back tomorrow.")
        return
    
    growth = random.randint(-5, 20)
    old_length, new_length, actual_growth, bonus = await db.do_grow(telegram_id, chat_id, growth)
    
    name = message.from_user.first_name or message.from_user.username or "User"
    
    if growth < 0:
        emoji = "📉"
        text = f"{emoji} {name} shrunk by {abs(growth)} cm!"
    elif growth == 0:
        emoji = "😐"
        text = f"{emoji} {name} didn't grow today."
    else:
        emoji = "📈"
        text = f"{emoji} {name} grew by {growth} cm!"
    
    if bonus > 0:
        text += f"\nDebt bonus: +{bonus:.1f} cm"
    
    text += f"\n\nTotal length: {new_length:.1f} cm"
    
    await message.answer(text)


@router.message(Command("top"))
async def cmd_top(message: Message):
    chat_id = message.chat.id
    leaderboard = await db.get_leaderboard(chat_id)
    
    if not leaderboard:
        await message.answer("No one has grown in this chat yet! Use /grow to start.")
        return
    
    text = "🏆 Leaderboard:\n\n"
    for i, user_chat in enumerate(leaderboard, 1):
        total = user_chat.length + user_chat.paid_length
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} User {user_chat.telegram_id}: {total:.1f} cm\n"
    
    await message.answer(text)


@router.message(Command("loan"))
async def cmd_loan(message: Message):
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    await db.get_or_create_user_chat(telegram_id, chat_id)
    
    success, new_length, debt = await db.apply_loan(telegram_id, chat_id)
    
    if success:
        await message.answer(
            f"Loan approved! Your length is now {new_length:.1f} cm.\n"
            f"Total debt: {debt:.1f} cm (will be repaid with future growth)"
        )
    else:
        await message.answer(
            f"You don't need a loan! Your length is {new_length:.1f} cm.\n"
            f"Current debt: {debt:.1f} cm"
        )


@router.message(Command("wallet"))
async def cmd_wallet(message: Message):
    telegram_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    
    if len(args) < 2:
        wallet = await db.get_wallet(telegram_id)
        if wallet:
            await message.answer(f"Your registered wallet: {wallet}")
        else:
            await message.answer("Usage: /wallet <SOL_ADDRESS>\n\nExample: /wallet So1anA...")
        return
    
    wallet_address = args[1].strip()
    if len(wallet_address) < 32 or len(wallet_address) > 44:
        await message.answer("Invalid Solana wallet address. Please provide a valid address.")
        return
    
    await db.set_wallet(telegram_id, wallet_address)
    await message.answer(f"Wallet registered: {wallet_address}")


@router.message(Command("buy"))
async def cmd_buy(message: Message):
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    args = message.text.split()
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    
    wallet = await db.get_wallet(telegram_id)
    if not wallet:
        await message.answer("Please register your wallet first using /wallet <SOL_ADDRESS>")
        return
    
    if len(args) < 2:
        text = "Available packages:\n\n"
        for num, pkg in PACKAGES.items():
            text += f"Package {num}: {pkg['growth']} cm for {pkg['price']:,} FAPCOIN\n"
        text += "\nUsage: /buy <package_number>"
        await message.answer(text)
        return
    
    try:
        package_num = int(args[1])
    except ValueError:
        await message.answer("Invalid package number. Use /buy to see available packages.")
        return
    
    if package_num not in PACKAGES:
        await message.answer("Invalid package number. Use /buy to see available packages.")
        return
    
    pkg = PACKAGES[package_num]
    team_wallet = os.environ.get('TEAM_WALLET_ADDRESS', 'Not configured')
    
    await message.answer(
        f"To purchase Package {package_num} ({pkg['growth']} cm):\n\n"
        f"Send {pkg['price']:,} $FAPCOIN to:\n"
        f"`{team_wallet}`\n\n"
        f"After sending, your growth will be credited automatically once verified.",
        parse_mode=ParseMode.MARKDOWN
    )


@router.message(Command("pvp"))
async def cmd_pvp(message: Message):
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    args = message.text.split()
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    await db.get_or_create_user_chat(telegram_id, chat_id)
    
    if len(args) < 3:
        await message.answer("Usage: /pvp @username <bet_amount>\n\nExample: /pvp @friend 10")
        return
    
    if not message.reply_to_message and not message.entities:
        await message.answer("Please mention a user to challenge.")
        return
    
    try:
        bet = float(args[-1])
        if bet <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("Invalid bet amount. Must be a positive number.")
        return
    
    total = await db.get_total_length(telegram_id, chat_id)
    if total < bet:
        await message.answer(f"Insufficient length! You have {total:.1f} cm but need {bet:.1f} cm to bet.")
        return
    
    await message.answer(
        f"PvP challenge created!\n"
        f"Bet: {bet:.1f} cm\n\n"
        f"Waiting for opponent to accept..."
    )


@router.message(Command("support"))
async def cmd_support(message: Message):
    telegram_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    
    if len(args) < 2:
        await message.answer(
            "Need help? Please provide your support username:\n\n"
            "Usage: /support @your_telegram_username\n\n"
            "Our team will contact you directly."
        )
        return
    
    support_username = args[1].strip()
    await db.create_support_request(telegram_id, support_username)
    
    await message.answer(
        f"Support request created!\n\n"
        f"We'll contact you at: {support_username}\n"
        f"Please wait for our team to respond."
    )


@router.inline_query()
async def inline_handler(inline_query: InlineQuery):
    query = inline_query.query.lower().strip()
    results = []
    
    if query.startswith("grow") or not query:
        results.append(
            InlineQueryResultArticle(
                id="grow",
                title="/grow",
                description="Get your daily growth",
                input_message_content=InputTextMessageContent(message_text="/grow")
            )
        )
    
    if query.startswith("top") or not query:
        results.append(
            InlineQueryResultArticle(
                id="top",
                title="/top",
                description="Show leaderboard",
                input_message_content=InputTextMessageContent(message_text="/top")
            )
        )
    
    if query.startswith("loan") or not query:
        results.append(
            InlineQueryResultArticle(
                id="loan",
                title="/loan",
                description="Reset debt to zero",
                input_message_content=InputTextMessageContent(message_text="/loan")
            )
        )
    
    if query.startswith("wallet") or not query:
        results.append(
            InlineQueryResultArticle(
                id="wallet",
                title="/wallet",
                description="Register your Solana wallet",
                input_message_content=InputTextMessageContent(message_text="/wallet")
            )
        )
    
    if query.startswith("buy") or not query:
        results.append(
            InlineQueryResultArticle(
                id="buy",
                title="/buy",
                description="Purchase growth packages",
                input_message_content=InputTextMessageContent(message_text="/buy")
            )
        )
    
    if query.startswith("support") or not query:
        results.append(
            InlineQueryResultArticle(
                id="support",
                title="/support",
                description="Request support",
                input_message_content=InputTextMessageContent(message_text="/support")
            )
        )
    
    await inline_query.answer(results[:10], cache_time=60)
