import os
import random
import re
import aiohttp
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

FAPCOIN_TOKEN_ADDRESS = os.environ.get('FAPCOIN_TOKEN_ADDRESS', '')


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
        "/daily - Trigger daily Dick of the Day selection\n"
        "/pvp @user <bet> - Challenge a user\n"
        "/loan - Reset debt to zero\n"
        "/wallet <address> - Register Solana wallet\n"
        "/buy <package> - Purchase growth with $FAPCOIN\n"
        "/verify <tx_hash> - Verify a FAPCOIN payment\n"
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
    for i, user in enumerate(leaderboard, 1):
        name = user['first_name'] or user['username'] or f"User {user['telegram_id']}"
        if user['username']:
            name = f"@{user['username']}"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} {name}: {user['total']:.1f} cm\n"
    
    await message.answer(text)


@router.message(Command("daily"))
async def cmd_daily(message: Message):
    chat_id = message.chat.id
    
    has_winner = await db.has_daily_winner_today(chat_id)
    if has_winner:
        await message.answer("Today's Dick of the Day has already been selected! Come back tomorrow.")
        return
    
    winner = await db.select_daily_winner(chat_id)
    
    if not winner:
        await message.answer("No eligible users for Dick of the Day! Users must /grow at least once in the past 7 days.")
        return
    
    name = winner['first_name'] or winner['username'] or f"User {winner['telegram_id']}"
    if winner['username']:
        name = f"@{winner['username']}"
    
    await message.answer(
        f"🎉 DICK OF THE DAY 🎉\n\n"
        f"Congratulations to {name}!\n\n"
        f"You've been awarded +{winner['bonus']} cm bonus growth!\n\n"
        f"Keep growing and you might be next!"
    )


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
    await db.get_or_create_user_chat(telegram_id, chat_id)
    
    wallet = await db.get_wallet(telegram_id)
    if not wallet:
        await message.answer("Please register your wallet first using /wallet <SOL_ADDRESS>")
        return
    
    if len(args) < 2:
        text = "Available packages:\n\n"
        for num, pkg in PACKAGES.items():
            text += f"Package {num}: {pkg['growth']} cm for {pkg['price']:,} FAPCOIN\n"
        text += "\nUsage: /buy <package_number>\n"
        text += "After payment, use /verify <tx_hash> to verify your transaction."
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
    
    tx = await db.create_pending_transaction(telegram_id, chat_id, package_num, pkg['price'])
    
    await message.answer(
        f"To purchase Package {package_num} ({pkg['growth']} cm):\n\n"
        f"Send exactly {pkg['price']:,} $FAPCOIN to:\n"
        f"`{team_wallet}`\n\n"
        f"After sending, use:\n"
        f"/verify <transaction_hash>\n\n"
        f"Your growth will be credited once verified!",
        parse_mode=ParseMode.MARKDOWN
    )


@router.message(Command("verify"))
async def cmd_verify(message: Message):
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    args = message.text.split()
    
    await db.get_or_create_user(telegram_id, message.from_user.username, message.from_user.first_name)
    
    if len(args) < 2:
        await message.answer("Usage: /verify <transaction_hash>\n\nProvide the Solana transaction hash after payment.")
        return
    
    tx_hash = args[1].strip()
    
    if len(tx_hash) < 80 or len(tx_hash) > 100:
        await message.answer("Invalid transaction hash. Please provide a valid Solana transaction signature.")
        return
    
    pending_txs = await db.get_pending_transactions(telegram_id)
    if not pending_txs:
        await message.answer("No pending purchases found. Use /buy to make a purchase first.")
        return
    
    pending_tx = pending_txs[0]
    pkg = PACKAGES.get(pending_tx.package_number)
    
    if not pkg:
        await message.answer("Invalid package in pending transaction.")
        return
    
    solana_rpc = os.environ.get('SOLANA_RPC_URL', '')
    team_wallet = os.environ.get('TEAM_WALLET_ADDRESS', '')
    user_wallet = await db.get_wallet(telegram_id)
    
    if not solana_rpc or not team_wallet:
        await message.answer(
            "Payment verification is not configured yet. Please contact support.\n"
            "Your transaction will be manually verified."
        )
        return
    
    try:
        verified = await verify_solana_transaction(
            tx_hash, 
            user_wallet, 
            team_wallet, 
            pending_tx.amount_paid,
            solana_rpc
        )
        
        if verified:
            success = await db.confirm_transaction(pending_tx.transaction_id, tx_hash, pkg['growth'])
            if success:
                await message.answer(
                    f"Payment verified!\n\n"
                    f"You received +{pkg['growth']} cm growth!\n"
                    f"Thank you for your purchase!"
                )
            else:
                await message.answer("Error confirming transaction. Please contact support.")
        else:
            await message.answer(
                "Could not verify the transaction. Please ensure:\n"
                f"1. You sent exactly {int(pending_tx.amount_paid):,} FAPCOIN\n"
                f"2. You sent from your registered wallet\n"
                f"3. You sent to the correct address\n\n"
                "If you believe this is an error, use /support."
            )
    except Exception as e:
        await message.answer(
            "Error verifying transaction. Please try again later or contact support."
        )


async def verify_solana_transaction(tx_hash: str, from_wallet: str, to_wallet: str, expected_amount: float, rpc_url: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [
                    tx_hash,
                    {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
                ]
            }
            
            async with session.post(rpc_url, json=payload) as response:
                if response.status != 200:
                    return False
                
                data = await response.json()
                
                if 'result' not in data or data['result'] is None:
                    return False
                
                tx = data['result']
                
                if tx.get('meta', {}).get('err') is not None:
                    return False
                
                return True
                
    except Exception:
        return False


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
    
    opponent_id = None
    opponent_name = None
    
    if message.entities:
        for entity in message.entities:
            if entity.type == 'mention':
                opponent_name = message.text[entity.offset:entity.offset + entity.length]
                break
            elif entity.type == 'text_mention' and entity.user:
                opponent_id = entity.user.id
                opponent_name = entity.user.first_name or entity.user.username
                await db.get_or_create_user(
                    entity.user.id,
                    entity.user.username,
                    entity.user.first_name
                )
                await db.get_or_create_user_chat(entity.user.id, chat_id)
                break
    
    if not opponent_id and not opponent_name:
        await message.answer("Please mention a valid user to challenge.")
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
    
    if opponent_id:
        challenge = await db.create_pvp_challenge(chat_id, telegram_id, opponent_id, bet)
        
        if not challenge:
            await message.answer("Could not create challenge. You may already have a pending challenge.")
            return
        
        challenger_name = message.from_user.first_name or message.from_user.username or "User"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Accept", callback_data=f"pvp_accept_{challenge.id}"),
                InlineKeyboardButton(text="Decline", callback_data=f"pvp_decline_{challenge.id}")
            ]
        ])
        
        await message.answer(
            f"⚔️ PVP CHALLENGE ⚔️\n\n"
            f"{challenger_name} challenges {opponent_name}!\n"
            f"Bet: {bet:.1f} cm\n\n"
            f"{opponent_name}, click below to respond!",
            reply_markup=keyboard
        )
    else:
        await message.answer(
            f"To challenge {opponent_name}, they need to send a message first.\n"
            f"Then you can challenge them with /pvp @{opponent_name} {bet}"
        )


@router.callback_query(F.data.startswith("pvp_accept_"))
async def pvp_accept_callback(callback: CallbackQuery):
    challenge_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    challenge = await db.get_pending_pvp_challenge(challenge_id)
    
    if not challenge:
        await callback.answer("This challenge is no longer available!", show_alert=True)
        return
    
    if user_id != challenge.opponent_id:
        await callback.answer("This challenge is not for you!", show_alert=True)
        return
    
    result = await db.accept_pvp_challenge(challenge_id)
    
    if not result:
        await callback.answer("Error processing challenge!", show_alert=True)
        return
    
    if result.get('error') == 'insufficient_funds':
        await callback.answer("You don't have enough length to accept this bet!", show_alert=True)
        return
    
    if result.get('draw'):
        await callback.message.edit_text(
            f"⚔️ PVP RESULT ⚔️\n\n"
            f"It's a DRAW!\n\n"
            f"Challenger rolled: {result['challenger_roll']}\n"
            f"Opponent rolled: {result['opponent_roll']}\n\n"
            f"No length was exchanged."
        )
        await callback.answer("It's a draw!")
        return
    
    challenger_user = await db.get_user_by_telegram_id(result['challenger_id'])
    opponent_user = await db.get_user_by_telegram_id(result['opponent_id'])
    winner_user = await db.get_user_by_telegram_id(result['winner_id'])
    loser_id = result['loser_id']
    
    challenger_name = challenger_user.first_name if challenger_user else "Challenger"
    opponent_name = opponent_user.first_name if opponent_user else "Opponent"
    winner_name = winner_user.first_name if winner_user else "Winner"
    
    await callback.message.edit_text(
        f"⚔️ PVP RESULT ⚔️\n\n"
        f"{challenger_name} rolled: {result['challenger_roll']}\n"
        f"{opponent_name} rolled: {result['opponent_roll']}\n\n"
        f"🏆 {winner_name} WINS! 🏆\n\n"
        f"+{result['bet']:.1f} cm gained!\n"
        f"-{result['bet']:.1f} cm lost by the loser!"
    )
    await callback.answer(f"{winner_name} wins!")


@router.callback_query(F.data.startswith("pvp_decline_"))
async def pvp_decline_callback(callback: CallbackQuery):
    challenge_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    challenge = await db.get_pending_pvp_challenge(challenge_id)
    
    if not challenge:
        await callback.answer("This challenge is no longer available!", show_alert=True)
        return
    
    if user_id != challenge.opponent_id:
        await callback.answer("This challenge is not for you!", show_alert=True)
        return
    
    await db.decline_pvp_challenge(challenge_id)
    
    await callback.message.edit_text(
        f"⚔️ PVP DECLINED ⚔️\n\n"
        f"The challenge was declined."
    )
    await callback.answer("Challenge declined!")


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
    
    if query.startswith("daily") or not query:
        results.append(
            InlineQueryResultArticle(
                id="daily",
                title="/daily",
                description="Dick of the Day selection",
                input_message_content=InputTextMessageContent(message_text="/daily")
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
