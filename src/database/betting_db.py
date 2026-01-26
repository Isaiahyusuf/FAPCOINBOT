import os
import random
import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.orm import selectinload

from .betting_models import (
    BettingBase, BetUserWallet, FapcoinBet, GroupOwnerWallet, 
    WithdrawalRequest, DepositTransaction, BetStatus
)

logger = logging.getLogger(__name__)

_betting_engine = None
_betting_session = None

def get_betting_database_url():
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
    
    url = os.environ.get('BETTING_DATABASE_URL') or os.environ.get('DATABASE_URL')
    if not url:
        return None
    
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    
    try:
        parsed = urlparse(url)
        
        scheme = 'postgresql+asyncpg'
        
        query_params = parse_qs(parsed.query)
        query_params.pop('sslmode', None)
        new_query = urlencode(query_params, doseq=True)
        
        port = parsed.port if parsed.port else 5432
        
        netloc = f"{parsed.username}:{parsed.password}@{parsed.hostname}:{port}" if parsed.password else f"{parsed.username}@{parsed.hostname}:{port}"
        
        new_url = urlunparse((scheme, netloc, parsed.path, '', new_query, ''))
        return new_url
    except Exception as e:
        logger.error(f"Error parsing database URL: {e}")
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql+asyncpg://', 1)
        elif url.startswith('postgresql://') and '+asyncpg' not in url:
            url = url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return url

def get_betting_engine():
    global _betting_engine
    if _betting_engine is None:
        url = get_betting_database_url()
        if not url:
            raise ValueError("No BETTING_DATABASE_URL or DATABASE_URL found")
        _betting_engine = create_async_engine(url, echo=False, pool_pre_ping=True)
    return _betting_engine

def get_betting_session():
    global _betting_session
    if _betting_session is None:
        engine = get_betting_engine()
        _betting_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return _betting_session

async def init_betting_db():
    engine = get_betting_engine()
    async with engine.begin() as conn:
        await conn.run_sync(BettingBase.metadata.create_all)
    logger.info("Betting database tables created successfully")

async def get_or_create_bet_wallet(telegram_id: int) -> BetUserWallet:
    from src.utils.wallet import generate_solana_keypair, encrypt_private_key
    
    Session = get_betting_session()
    async with Session() as session:
        result = await session.execute(
            select(BetUserWallet).where(BetUserWallet.telegram_id == telegram_id)
        )
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            public_key, private_key = generate_solana_keypair()
            encrypted_key = encrypt_private_key(private_key)
            
            wallet = BetUserWallet(
                telegram_id=telegram_id,
                public_key=public_key,
                encrypted_private_key=encrypted_key,
                balance=0.0
            )
            session.add(wallet)
            await session.commit()
            await session.refresh(wallet)
            logger.info(f"Created new betting wallet for user {telegram_id}")
        
        return wallet

async def get_bet_wallet(telegram_id: int) -> BetUserWallet | None:
    Session = get_betting_session()
    async with Session() as session:
        result = await session.execute(
            select(BetUserWallet).where(BetUserWallet.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

async def add_bet_wallet_balance(telegram_id: int, amount: float) -> tuple:
    Session = get_betting_session()
    async with Session() as session:
        result = await session.execute(
            select(BetUserWallet).where(BetUserWallet.telegram_id == telegram_id).with_for_update()
        )
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            return False, 0.0, "wallet_not_found"
        
        wallet.balance += amount
        wallet.total_deposited += amount
        wallet.updated_at = datetime.utcnow()
        await session.commit()
        
        return True, wallet.balance, None

async def deduct_bet_wallet_balance(telegram_id: int, amount: float) -> tuple:
    Session = get_betting_session()
    async with Session() as session:
        result = await session.execute(
            select(BetUserWallet).where(BetUserWallet.telegram_id == telegram_id).with_for_update()
        )
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            return False, 0.0, "wallet_not_found"
        if wallet.balance < amount:
            return False, wallet.balance, "insufficient_balance"
        
        wallet.balance -= amount
        wallet.updated_at = datetime.utcnow()
        await session.commit()
        
        return True, wallet.balance, None

async def create_fapcoin_bet(chat_id: int, challenger_id: int, opponent_id: int | None, 
                              bet_amount: float, opponent_username: str = None) -> FapcoinBet | None:
    Session = get_betting_session()
    async with Session() as session:
        result = await session.execute(
            select(BetUserWallet).where(BetUserWallet.telegram_id == challenger_id).with_for_update()
        )
        challenger_wallet = result.scalar_one_or_none()
        
        if not challenger_wallet or challenger_wallet.balance < bet_amount:
            return None
        
        bet = FapcoinBet(
            chat_id=chat_id,
            challenger_id=challenger_id,
            opponent_id=opponent_id,
            opponent_username=opponent_username,
            bet_amount=bet_amount,
            status=BetStatus.PENDING
        )
        session.add(bet)
        await session.commit()
        await session.refresh(bet)
        
        logger.info(f"Created FAPCOIN bet {bet.id}: {challenger_id} vs {opponent_id or opponent_username} for {bet_amount}")
        return bet

async def get_pending_fapcoin_bet(bet_id: int) -> FapcoinBet | None:
    Session = get_betting_session()
    async with Session() as session:
        result = await session.execute(
            select(FapcoinBet).where(
                and_(FapcoinBet.id == bet_id, FapcoinBet.status == BetStatus.PENDING)
            )
        )
        return result.scalar_one_or_none()

async def has_pending_bet_between(chat_id: int, user1_id: int, user2_id: int) -> bool:
    Session = get_betting_session()
    async with Session() as session:
        result = await session.execute(
            select(FapcoinBet).where(
                and_(
                    FapcoinBet.chat_id == chat_id,
                    FapcoinBet.status == BetStatus.PENDING,
                    or_(
                        and_(FapcoinBet.challenger_id == user1_id, FapcoinBet.opponent_id == user2_id),
                        and_(FapcoinBet.challenger_id == user2_id, FapcoinBet.opponent_id == user1_id)
                    )
                )
            )
        )
        return result.scalar_one_or_none() is not None

async def update_bet_opponent_id(bet_id: int, opponent_id: int):
    Session = get_betting_session()
    async with Session() as session:
        await session.execute(
            update(FapcoinBet).where(FapcoinBet.id == bet_id).values(opponent_id=opponent_id)
        )
        await session.commit()

async def accept_fapcoin_bet(bet_id: int, treasury_wallet: str, dev_wallet: str, 
                              group_owner_wallet: str = None, is_main_group: bool = False) -> dict:
    from src.utils.wallet import calculate_bet_distribution
    
    Session = get_betting_session()
    async with Session() as session:
        result = await session.execute(
            select(FapcoinBet).where(FapcoinBet.id == bet_id).with_for_update()
        )
        bet = result.scalar_one_or_none()
        
        if not bet or bet.status != BetStatus.PENDING:
            return {"error": "bet_not_found"}
        
        challenger_result = await session.execute(
            select(BetUserWallet).where(BetUserWallet.telegram_id == bet.challenger_id).with_for_update()
        )
        challenger_wallet = challenger_result.scalar_one_or_none()
        
        opponent_result = await session.execute(
            select(BetUserWallet).where(BetUserWallet.telegram_id == bet.opponent_id).with_for_update()
        )
        opponent_wallet = opponent_result.scalar_one_or_none()
        
        if not challenger_wallet or challenger_wallet.balance < bet.bet_amount:
            bet.status = BetStatus.CANCELLED
            await session.commit()
            return {"error": "challenger_insufficient_balance"}
        
        if not opponent_wallet or opponent_wallet.balance < bet.bet_amount:
            return {"error": "opponent_insufficient_balance"}
        
        challenger_wallet.balance -= bet.bet_amount
        opponent_wallet.balance -= bet.bet_amount
        
        challenger_roll = random.randint(1, 100)
        opponent_roll = random.randint(1, 100)
        
        bet.challenger_roll = challenger_roll
        bet.opponent_roll = opponent_roll
        
        if challenger_roll == opponent_roll:
            challenger_wallet.balance += bet.bet_amount
            opponent_wallet.balance += bet.bet_amount
            bet.status = BetStatus.COMPLETED
            bet.resolved_at = datetime.utcnow()
            await session.commit()
            return {
                "draw": True,
                "challenger_roll": challenger_roll,
                "opponent_roll": opponent_roll
            }
        
        total_pot = Decimal(str(bet.bet_amount)) * 2
        distribution = calculate_bet_distribution(float(total_pot), is_main_group=is_main_group)
        
        winner_id = bet.challenger_id if challenger_roll > opponent_roll else bet.opponent_id
        loser_id = bet.opponent_id if challenger_roll > opponent_roll else bet.challenger_id
        
        winner_wallet = challenger_wallet if winner_id == bet.challenger_id else opponent_wallet
        loser_wallet = opponent_wallet if winner_id == bet.challenger_id else challenger_wallet
        
        winner_wallet.balance += distribution["winner"]
        winner_wallet.total_won += distribution["winner"]
        winner_wallet.bets_won += 1
        
        loser_wallet.total_lost += bet.bet_amount
        loser_wallet.bets_lost += 1
        
        bet.winner_id = winner_id
        bet.winner_payout = distribution["winner"]
        bet.treasury_fee = distribution["treasury"]
        bet.group_owner_fee = distribution["group_owner"]
        bet.dev_fee = 0.0
        bet.status = BetStatus.COMPLETED
        bet.resolved_at = datetime.utcnow()
        
        await session.commit()
        
        logger.info(f"Bet {bet_id} completed: winner={winner_id}, payout={distribution['winner']}")
        
        return {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "challenger_roll": challenger_roll,
            "opponent_roll": opponent_roll,
            "winner_payout": distribution["winner"],
            "treasury_fee": distribution["treasury"],
            "group_owner_fee": distribution["group_owner"],
            "total_pot": float(total_pot)
        }

async def decline_fapcoin_bet(bet_id: int):
    Session = get_betting_session()
    async with Session() as session:
        await session.execute(
            update(FapcoinBet).where(FapcoinBet.id == bet_id).values(
                status=BetStatus.DECLINED,
                resolved_at=datetime.utcnow()
            )
        )
        await session.commit()

async def get_or_create_group_owner_wallet(chat_id: int, wallet_address: str, set_by_user_id: int) -> GroupOwnerWallet:
    Session = get_betting_session()
    async with Session() as session:
        result = await session.execute(
            select(GroupOwnerWallet).where(GroupOwnerWallet.chat_id == chat_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.wallet_address = wallet_address
            existing.set_by_user_id = set_by_user_id
            existing.updated_at = datetime.utcnow()
            await session.commit()
            return existing
        
        wallet = GroupOwnerWallet(
            chat_id=chat_id,
            wallet_address=wallet_address,
            set_by_user_id=set_by_user_id
        )
        session.add(wallet)
        await session.commit()
        await session.refresh(wallet)
        return wallet

async def get_group_owner_wallet(chat_id: int) -> str | None:
    Session = get_betting_session()
    async with Session() as session:
        result = await session.execute(
            select(GroupOwnerWallet).where(GroupOwnerWallet.chat_id == chat_id)
        )
        wallet = result.scalar_one_or_none()
        return wallet.wallet_address if wallet else None

async def create_withdrawal_request(telegram_id: int, amount: float, destination: str) -> WithdrawalRequest:
    Session = get_betting_session()
    async with Session() as session:
        withdrawal = WithdrawalRequest(
            telegram_id=telegram_id,
            amount=amount,
            destination_address=destination,
            status="pending"
        )
        session.add(withdrawal)
        await session.commit()
        await session.refresh(withdrawal)
        return withdrawal

async def delete_bet_wallet(telegram_id: int) -> bool:
    Session = get_betting_session()
    async with Session() as session:
        result = await session.execute(
            select(BetUserWallet).where(BetUserWallet.telegram_id == telegram_id)
        )
        wallet = result.scalar_one_or_none()
        
        if wallet:
            await session.delete(wallet)
            await session.commit()
            return True
        return False

async def get_betting_stats(chat_id: int = None) -> dict:
    Session = get_betting_session()
    async with Session() as session:
        if chat_id:
            result = await session.execute(
                select(FapcoinBet).where(
                    and_(FapcoinBet.chat_id == chat_id, FapcoinBet.status == BetStatus.COMPLETED)
                )
            )
        else:
            result = await session.execute(
                select(FapcoinBet).where(FapcoinBet.status == BetStatus.COMPLETED)
            )
        
        bets = result.scalars().all()
        
        total_bets = len(bets)
        total_volume = sum(b.bet_amount * 2 for b in bets)
        total_fees = sum((b.treasury_fee or 0) + (b.group_owner_fee or 0) for b in bets)
        
        return {
            "total_bets": total_bets,
            "total_volume": total_volume,
            "total_fees": total_fees
        }
