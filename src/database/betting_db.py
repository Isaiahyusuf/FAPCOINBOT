"""
Betting database module - all tables are now in models.py
This module is kept for backwards compatibility only.
"""
import logging

logger = logging.getLogger(__name__)


async def init_betting_db():
    """No-op - betting tables are created by init_db() in models.py"""
    logger.info("Betting tables are managed by main database init")
    pass
