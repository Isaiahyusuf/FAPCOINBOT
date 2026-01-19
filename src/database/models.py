import os
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    wallet_address = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserChat(Base):
    __tablename__ = 'user_chats'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    length = Column(Float, default=0.0)
    paid_length = Column(Float, default=0.0)
    debt = Column(Float, default=0.0)
    last_grow = Column(DateTime, nullable=True)
    last_active = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(255), unique=True, nullable=False)
    telegram_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    amount_paid = Column(Float, nullable=False)
    package_number = Column(Integer, nullable=False)
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyWinner(Base):
    __tablename__ = 'daily_winners'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False)
    telegram_id = Column(BigInteger, nullable=False)
    date = Column(DateTime, nullable=False)
    bonus_growth = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PvpChallenge(Base):
    __tablename__ = 'pvp_challenges'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False)
    challenger_id = Column(BigInteger, nullable=False)
    opponent_id = Column(BigInteger, nullable=False)
    opponent_username = Column(String(255), nullable=True)  # For @mention matching
    bet_amount = Column(Float, nullable=False)
    status = Column(String(50), default='pending')
    winner_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SupportRequest(Base):
    __tablename__ = 'support_requests'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    support_username = Column(String(255), nullable=False)
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)


class BotSettings(Base):
    __tablename__ = 'bot_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(String(1024), nullable=False)
    updated_by = Column(BigInteger, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_database_url():
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


async def init_db():
    try:
        sync_url = get_sync_database_url()
        engine = create_engine(sync_url)
        Base.metadata.create_all(engine)
        engine.dispose()
    except Exception as e:
        print(f"Database initialization error: {e}")
        print(f"DATABASE_URL format: {os.environ.get('DATABASE_URL', 'NOT SET')[:50]}...")
        raise


def create_async_session():
    url = get_database_url()
    engine = create_async_engine(url, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
