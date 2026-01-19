import os
import asyncio
import logging
from datetime import datetime, time
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from src.database.models import init_db
from src.database import db
from src.handlers.commands import router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    logger.info("Database initialized successfully!")
    
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    dp.include_router(router)
    
    asyncio.create_task(daily_winner_task(bot))
    
    logger.info("Starting FAPCOIN DICK BOT...")
    logger.info("Daily winner selection task started (runs at 12:00 UTC)")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
