import os
import asyncio
import logging
import random
from datetime import datetime, time
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats, InlineKeyboardMarkup, InlineKeyboardButton

from src.database.models import init_db
from src.database import db
from src.database.betting_db import init_betting_db
from src.handlers.commands import router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROMO_MESSAGES = [
    {
        "text": "🍆 <b>Who's got the biggest one?</b> 🍆\n\n"
                "Use /grow to find out!\n"
                "Will you grow or shrink today? 😏",
        "button": "🌱 Grow Now!"
    },
    {
        "text": "⚔️ <b>BATTLE TIME!</b> ⚔️\n\n"
                "Think you're bigger than your friends?\n"
                "Tag them with <code>@username /pvp 5</code> to prove it!",
        "button": "⚔️ Start Battle"
    },
    {
        "text": "🏆 <b>LEADERBOARD UPDATE</b> 🏆\n\n"
                "Who's dominating the group today?\n"
                "Check /top to see the rankings!",
        "button": "🏆 View Top"
    },
    {
        "text": "💰 <b>WANT INSTANT GROWTH?</b> 💰\n\n"
                "Skip the grind! Buy growth with $FAPCOIN!\n"
                "Use /buy to see packages 🚀",
        "button": "💰 Buy Growth"
    },
    {
        "text": "🎲 <b>DAILY CHALLENGE!</b> 🎲\n\n"
                "Have you grown today?\n"
                "Don't miss your daily growth chance! 🍀",
        "button": "🌱 Daily Grow"
    },
    {
        "text": "😈 <b>FEELING RISKY?</b> 😈\n\n"
                "Challenge someone to a PvP battle!\n"
                "Winner takes all! Reply to someone + <code>/pvp 10</code>",
        "button": "⚔️ Challenge"
    },
    {
        "text": "📈 <b>GROWTH REPORT</b> 📈\n\n"
                "Some of you are MASSIVE! 🍆\n"
                "Others... not so much 😂\n\n"
                "Use /top to see where you stand!",
        "button": "📊 Check Stats"
    },
    {
        "text": "🔥 <b>HOT TIP!</b> 🔥\n\n"
                "Win PvP battles to steal cm from others!\n"
                "Tag + <code>/pvp [bet]</code> to challenge! ⚔️",
        "button": "⚔️ Fight Now"
    },
    {
        "text": "🍆 <b>Interested in a bigger dick?</b> 🍆\n\n"
                "Every purchase in $FAPCOIN is sent to our treasury wallet\n"
                "to continue to support the project! 💎\n\n"
                "Use /buy to grow instantly!",
        "button": "💰 Support & Grow"
    },
]


async def promo_message_task(bot: Bot):
    """Send promotional messages to active groups every hour."""
    await asyncio.sleep(60)  # Wait 1 minute before first promo
    
    while True:
        try:
            active_chats = await db.get_active_chats()
            
            if active_chats:
                promo = random.choice(PROMO_MESSAGES)
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=promo["button"], callback_data="action_menu")]
                ])
                
                for chat_id in active_chats:
                    try:
                        await bot.send_message(
                            chat_id,
                            promo["text"],
                            reply_markup=keyboard,
                            parse_mode=ParseMode.HTML
                        )
                        logger.info(f"Sent promo to chat {chat_id}")
                    except Exception as e:
                        logger.warning(f"Could not send promo to chat {chat_id}: {e}")
                    
                    await asyncio.sleep(1)  # Small delay between chats
            
            await asyncio.sleep(3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Error in promo task: {e}")
            await asyncio.sleep(60)


async def daily_winner_task(bot: Bot):
    while True:
        try:
            now = datetime.utcnow()
            target_hour = 12
            
            if now.hour == target_hour:
                logger.info("Running daily winner selection...")
                active_chats = await db.get_active_chats()
                
                for chat_id in active_chats:
                    try:
                        winner = await db.select_daily_winner(chat_id)
                        if winner:
                            name = winner['first_name'] or winner['username'] or f"User {winner['telegram_id']}"
                            if winner['username']:
                                name = f"@{winner['username']}"
                            
                            await bot.send_message(
                                chat_id,
                                f"🎉 DICK OF THE DAY 🎉\n\n"
                                f"Congratulations to {name}!\n\n"
                                f"You've been awarded +{winner['bonus']} cm bonus growth!\n\n"
                                f"Keep growing and you might be next!"
                            )
                            logger.info(f"Daily winner selected for chat {chat_id}")
                    except Exception as e:
                        logger.error(f"Error selecting daily winner for chat {chat_id}: {e}")
                
                await asyncio.sleep(3600)
            else:
                await asyncio.sleep(300)
                
        except Exception as e:
            logger.error(f"Error in daily winner task: {e}")
            await asyncio.sleep(60)


async def main():
    bot_token = os.environ.get('BOT_TOKEN')
    
    if not bot_token:
        logger.error("BOT_TOKEN environment variable is not set!")
        logger.info("Please set the BOT_TOKEN secret to run the bot.")
        logger.info("Waiting for BOT_TOKEN to be configured...")
        while True:
            await asyncio.sleep(60)
            bot_token = os.environ.get('BOT_TOKEN')
            if bot_token:
                break
    
    logger.info("Initializing database...")
    await init_db()
    logger.info("Main database initialized successfully!")
    
    logger.info("Initializing betting database...")
    await init_betting_db()
    logger.info("Betting database initialized successfully!")
    
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Add error handler to log all unhandled exceptions
    @dp.errors()
    async def error_handler(event, exception):
        logger.error(f"UNHANDLED ERROR: {exception}")
        logger.error(f"Event: {event}")
        import traceback
        logger.error(traceback.format_exc())
        return True
    
    dp.include_router(router)
    logger.info(f"Router included with {len(router.message.handlers)} message handlers")
    
    group_commands = [
        BotCommand(command="menu", description="🎮 Open main menu"),
        BotCommand(command="grow", description="🌱 Daily growth"),
        BotCommand(command="top", description="🏆 View leaderboard"),
        BotCommand(command="pvp", description="⚔️ PvP battle (bet cm)"),
        BotCommand(command="fapbet", description="💰 Bet FAPCOIN tokens"),
        BotCommand(command="wallet", description="💳 Your FAPCOIN wallet"),
        BotCommand(command="deposit", description="📥 Check for deposits"),
        BotCommand(command="withdraw", description="📤 Withdraw FAPCOIN"),
        BotCommand(command="daily", description="🎲 Dick of the Day"),
        BotCommand(command="buy", description="🛒 Buy growth with FAPCOIN"),
        BotCommand(command="gift", description="🎁 Gift cm to someone"),
        BotCommand(command="loan", description="💳 Reset negative length"),
        BotCommand(command="verify", description="✅ Verify payment"),
        BotCommand(command="setgroupwallet", description="👑 Set group owner wallet"),
        BotCommand(command="betstats", description="📊 View betting stats"),
        BotCommand(command="support", description="🆘 Contact support"),
        BotCommand(command="help", description="❓ Show all commands"),
    ]
    
    private_commands = [
        BotCommand(command="start", description="🚀 Start the bot"),
        BotCommand(command="menu", description="🎮 Open main menu"),
        BotCommand(command="wallet", description="💳 Your FAPCOIN wallet"),
        BotCommand(command="deposit", description="📥 Check for deposits"),
        BotCommand(command="withdraw", description="📤 Withdraw FAPCOIN"),
        BotCommand(command="support", description="🆘 Contact support"),
        BotCommand(command="help", description="❓ Show all commands"),
    ]
    
    await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
    await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    logger.info("Bot commands registered for groups and private chats")
    
    asyncio.create_task(daily_winner_task(bot))
    asyncio.create_task(promo_message_task(bot))
    
    logger.info("Starting FAPCOIN DICK BOT...")
    logger.info("Daily winner selection task started (runs at 12:00 UTC)")
    logger.info("Promo message task started (runs every hour)")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
