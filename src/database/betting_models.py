from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

BettingBase = declarative_base()

class BetStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class BetUserWallet(BettingBase):
    __tablename__ = "bet_user_wallets"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    public_key = Column(String(64), unique=True, nullable=False)
    encrypted_private_key = Column(Text, nullable=False)
    balance = Column(Float, default=0.0)
    total_deposited = Column(Float, default=0.0)
    total_withdrawn = Column(Float, default=0.0)
    total_won = Column(Float, default=0.0)
    total_lost = Column(Float, default=0.0)
    bets_won = Column(Integer, default=0)
    bets_lost = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FapcoinBet(BettingBase):
    __tablename__ = "fapcoin_bets"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    challenger_id = Column(BigInteger, nullable=False, index=True)
    opponent_id = Column(BigInteger, nullable=True, index=True)
    opponent_username = Column(String(64), nullable=True)
    bet_amount = Column(Float, nullable=False)
    status = Column(SQLEnum(BetStatus), default=BetStatus.PENDING)
    winner_id = Column(BigInteger, nullable=True)
    challenger_roll = Column(Integer, nullable=True)
    opponent_roll = Column(Integer, nullable=True)
    winner_payout = Column(Float, nullable=True)
    treasury_fee = Column(Float, nullable=True)
    dev_fee = Column(Float, nullable=True)
    group_owner_fee = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

class GroupOwnerWallet(BettingBase):
    __tablename__ = "group_owner_wallets"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    wallet_address = Column(String(64), nullable=False)
    set_by_user_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WithdrawalRequest(BettingBase):
    __tablename__ = "withdrawal_requests"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    destination_address = Column(String(64), nullable=False)
    status = Column(String(20), default="pending")
    tx_signature = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

class DepositTransaction(BettingBase):
    __tablename__ = "deposit_transactions"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    tx_signature = Column(String(128), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
