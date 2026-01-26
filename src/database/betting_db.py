"""
Betting database module - uses the same DATABASE_URL as main database
"""
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from .betting_models import BettingBase

logger = logging.getLogger(__name__)

_betting_engine = None
_betting_session = None


def get_database_url():
    """Get async database URL - same as main database"""
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql+asyncpg://', 1)
    elif url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    elif not url.startswith('postgresql+asyncpg://'):
        url = 'postgresql+asyncpg://' + url.split('://', 1)[-1] if '://' in url else url
    return url


def get_sync_database_url():
    """Get sync database URL for table creation"""
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    elif url.startswith('postgresql+asyncpg://'):
        url = url.replace('postgresql+asyncpg://', 'postgresql://', 1)
    elif not url.startswith('postgresql://'):
        url = 'postgresql://' + url.split('://', 1)[-1] if '://' in url else url
    return url


def get_betting_engine():
    global _betting_engine
    if _betting_engine is None:
        url = get_database_url()
        _betting_engine = create_async_engine(url, echo=False)
    return _betting_engine


def get_betting_session():
    global _betting_session
    if _betting_session is None:
        engine = get_betting_engine()
        _betting_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return _betting_session


async def init_betting_db():
    """Initialize betting tables in the same database"""
    from sqlalchemy import create_engine
    
    try:
        sync_url = get_sync_database_url()
        engine = create_engine(sync_url)
        
        BettingBase.metadata.create_all(engine)
        logger.info("Betting tables created successfully!")
        
        engine.dispose()
    except Exception as e:
        logger.error(f"Error initializing betting tables: {e}")
        raise
