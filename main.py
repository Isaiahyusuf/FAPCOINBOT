import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from src.database.models import init_db
from src.handlers.commands import router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    
    logger.info("Starting FAPCOIN DICK BOT...")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
