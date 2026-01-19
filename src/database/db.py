from datetime import datetime, timedelta
from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, UserChat, Transaction, DailyWinner, PvpChallenge, SupportRequest, create_async_session


SessionLocal = None


def get_session():
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = create_async_session()
    return SessionLocal


async def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None) -> User:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id, username=username, first_name=first_name)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def get_or_create_user_chat(telegram_id: int, chat_id: int) -> UserChat:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == telegram_id, UserChat.chat_id == chat_id)
            )
        )
        user_chat = result.scalar_one_or_none()
        if not user_chat:
            user_chat = UserChat(telegram_id=telegram_id, chat_id=chat_id)
            session.add(user_chat)
            await session.commit()
            await session.refresh(user_chat)
        return user_chat


async def can_grow_today(telegram_id: int, chat_id: int) -> bool:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == telegram_id, UserChat.chat_id == chat_id)
            )
        )
        user_chat = result.scalar_one_or_none()
        if not user_chat or not user_chat.last_grow:
            return True
        now = datetime.utcnow()
        last_grow = user_chat.last_grow
        return now.date() > last_grow.date()


async def do_grow(telegram_id: int, chat_id: int, growth: float) -> tuple:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == telegram_id, UserChat.chat_id == chat_id)
            )
        )
        user_chat = result.scalar_one_or_none()
        if not user_chat:
            user_chat = UserChat(telegram_id=telegram_id, chat_id=chat_id)
            session.add(user_chat)
        
        old_length = user_chat.length
        bonus = 0
        if old_length < 0:
            bonus = abs(old_length) * 0.002 * growth if growth > 0 else 0
        
        actual_growth = growth + bonus
        
        if user_chat.debt > 0 and actual_growth > 0:
            repayment = min(user_chat.debt, actual_growth * 0.2)
            user_chat.debt -= repayment
            actual_growth -= repayment
        
        user_chat.length += actual_growth
        user_chat.last_grow = datetime.utcnow()
        user_chat.last_active = datetime.utcnow()
        
        await session.commit()
        return old_length, user_chat.length, actual_growth, bonus


async def get_total_length(telegram_id: int, chat_id: int) -> float:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == telegram_id, UserChat.chat_id == chat_id)
            )
        )
        user_chat = result.scalar_one_or_none()
        if not user_chat:
            return 0.0
        return user_chat.length + user_chat.paid_length


async def get_leaderboard(chat_id: int, limit: int = 10) -> list:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(UserChat)
            .where(UserChat.chat_id == chat_id)
            .order_by((UserChat.length + UserChat.paid_length).desc())
            .limit(limit)
        )
        return result.scalars().all()


async def apply_loan(telegram_id: int, chat_id: int) -> tuple:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == telegram_id, UserChat.chat_id == chat_id)
            )
        )
        user_chat = result.scalar_one_or_none()
        if not user_chat:
            return False, 0, 0
        
        if user_chat.length >= 0:
            return False, user_chat.length, user_chat.debt
        
        debt_amount = abs(user_chat.length)
        user_chat.debt += debt_amount
        user_chat.length = 0
        
        await session.commit()
        return True, user_chat.length, user_chat.debt


async def set_wallet(telegram_id: int, wallet_address: str) -> bool:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            user.wallet_address = wallet_address
            await session.commit()
            return True
        return False


async def get_wallet(telegram_id: int) -> str:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        return user.wallet_address if user else None


async def add_paid_growth(telegram_id: int, chat_id: int, growth: float, transaction_id: str, package_number: int) -> bool:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == telegram_id, UserChat.chat_id == chat_id)
            )
        )
        user_chat = result.scalar_one_or_none()
        if not user_chat:
            user_chat = UserChat(telegram_id=telegram_id, chat_id=chat_id)
            session.add(user_chat)
        
        user_chat.paid_length += growth
        
        transaction = Transaction(
            transaction_id=transaction_id,
            telegram_id=telegram_id,
            chat_id=chat_id,
            amount_paid=growth,
            package_number=package_number,
            status='confirmed'
        )
        session.add(transaction)
        
        await session.commit()
        return True


async def get_eligible_users_for_daily(chat_id: int) -> list:
    Session = get_session()
    async with Session() as session:
        week_ago = datetime.utcnow() - timedelta(days=7)
        result = await session.execute(
            select(UserChat)
            .where(
                and_(
                    UserChat.chat_id == chat_id,
                    UserChat.last_grow >= week_ago
                )
            )
        )
        return result.scalars().all()


async def record_daily_winner(chat_id: int, telegram_id: int, bonus: float):
    Session = get_session()
    async with Session() as session:
        winner = DailyWinner(
            chat_id=chat_id,
            telegram_id=telegram_id,
            date=datetime.utcnow(),
            bonus_growth=bonus
        )
        session.add(winner)
        
        result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == telegram_id, UserChat.chat_id == chat_id)
            )
        )
        user_chat = result.scalar_one_or_none()
        if user_chat:
            user_chat.length += bonus
        
        await session.commit()


async def create_pvp_challenge(chat_id: int, challenger_id: int, opponent_id: int, bet: float) -> PvpChallenge:
    Session = get_session()
    async with Session() as session:
        challenger_result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == challenger_id, UserChat.chat_id == chat_id)
            )
        )
        challenger = challenger_result.scalar_one_or_none()
        if not challenger or (challenger.length + challenger.paid_length) < bet:
            return None
        
        challenge = PvpChallenge(
            chat_id=chat_id,
            challenger_id=challenger_id,
            opponent_id=opponent_id,
            bet_amount=bet
        )
        session.add(challenge)
        await session.commit()
        await session.refresh(challenge)
        return challenge


async def resolve_pvp(challenge_id: int, winner_id: int) -> bool:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(PvpChallenge).where(PvpChallenge.id == challenge_id)
        )
        challenge = result.scalar_one_or_none()
        if not challenge or challenge.status != 'pending':
            return False
        
        loser_id = challenge.opponent_id if winner_id == challenge.challenger_id else challenge.challenger_id
        
        winner_result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == winner_id, UserChat.chat_id == challenge.chat_id)
            )
        )
        winner_chat = winner_result.scalar_one_or_none()
        
        loser_result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == loser_id, UserChat.chat_id == challenge.chat_id)
            )
        )
        loser_chat = loser_result.scalar_one_or_none()
        
        if winner_chat:
            winner_chat.length += challenge.bet_amount
        if loser_chat:
            loser_chat.length -= challenge.bet_amount
        
        challenge.status = 'resolved'
        challenge.winner_id = winner_id
        
        await session.commit()
        return True


async def create_support_request(telegram_id: int, support_username: str) -> SupportRequest:
    Session = get_session()
    async with Session() as session:
        request = SupportRequest(
            telegram_id=telegram_id,
            support_username=support_username
        )
        session.add(request)
        await session.commit()
        await session.refresh(request)
        return request
