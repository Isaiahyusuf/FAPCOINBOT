from datetime import datetime, timedelta
import random
from sqlalchemy import select, update, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, UserChat, Transaction, DailyWinner, PvpChallenge, SupportRequest, BotSettings, create_async_session


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
        else:
            if username and user.username != username:
                user.username = username
            if first_name and user.first_name != first_name:
                user.first_name = first_name
            await session.commit()
        return user


async def get_user_by_telegram_id(telegram_id: int) -> User:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def get_user_by_username(username: str) -> User:
    """Find user by their Telegram username (case insensitive). Returns most recent if multiple found."""
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(User)
            .where(func.lower(User.username) == username.lower())
            .order_by(User.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


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
            # New players start with 10-20 cm
            starting_length = random.randint(10, 20)
            user_chat = UserChat(telegram_id=telegram_id, chat_id=chat_id, length=starting_length)
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
        )
        user_chats = result.scalars().all()
        
        # Deduplicate by telegram_id, keeping highest total
        seen_users = {}
        for uc in user_chats:
            total = uc.length + uc.paid_length
            if uc.telegram_id not in seen_users:
                seen_users[uc.telegram_id] = uc
            else:
                existing_total = seen_users[uc.telegram_id].length + seen_users[uc.telegram_id].paid_length
                if total > existing_total:
                    seen_users[uc.telegram_id] = uc
        
        # Sort by total and limit
        sorted_users = sorted(seen_users.values(), key=lambda x: x.length + x.paid_length, reverse=True)[:limit]
        
        leaderboard = []
        seen_usernames = set()
        for uc in sorted_users:
            user_result = await session.execute(
                select(User).where(User.telegram_id == uc.telegram_id)
            )
            user = user_result.scalar_one_or_none()
            username = user.username if user else None
            
            # Also skip if username already seen (handles same username different IDs)
            if username and username.lower() in seen_usernames:
                continue
            if username:
                seen_usernames.add(username.lower())
            
            leaderboard.append({
                'telegram_id': uc.telegram_id,
                'username': username,
                'first_name': user.first_name if user else None,
                'length': uc.length,
                'paid_length': uc.paid_length,
                'total': uc.length + uc.paid_length
            })
            
            if len(leaderboard) >= limit:
                break
        return leaderboard


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


async def create_pending_transaction(telegram_id: int, chat_id: int, package_number: int, expected_amount: float) -> Transaction:
    Session = get_session()
    async with Session() as session:
        import uuid
        tx_id = f"pending_{uuid.uuid4().hex[:16]}"
        transaction = Transaction(
            transaction_id=tx_id,
            telegram_id=telegram_id,
            chat_id=chat_id,
            amount_paid=expected_amount,
            package_number=package_number,
            status='pending'
        )
        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)
        return transaction


async def get_pending_transactions(telegram_id: int) -> list:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(Transaction).where(
                and_(
                    Transaction.telegram_id == telegram_id,
                    Transaction.status == 'pending'
                )
            ).order_by(Transaction.created_at.desc())
        )
        return result.scalars().all()


async def is_transaction_already_used(tx_hash: str) -> bool:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(Transaction).where(
                and_(
                    Transaction.transaction_id == tx_hash,
                    Transaction.status == 'confirmed'
                )
            )
        )
        return result.scalar_one_or_none() is not None


async def confirm_transaction(transaction_id: str, on_chain_tx_id: str, growth: float) -> bool:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        )
        tx = result.scalar_one_or_none()
        if not tx or tx.status != 'pending':
            return False
        
        tx.status = 'confirmed'
        tx.transaction_id = on_chain_tx_id
        
        uc_result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == tx.telegram_id, UserChat.chat_id == tx.chat_id)
            )
        )
        user_chat = uc_result.scalar_one_or_none()
        if not user_chat:
            user_chat = UserChat(telegram_id=tx.telegram_id, chat_id=tx.chat_id)
            session.add(user_chat)
        
        user_chat.paid_length += growth
        
        await session.commit()
        return True


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


async def has_daily_winner_today(chat_id: int) -> bool:
    Session = get_session()
    async with Session() as session:
        today = datetime.utcnow().date()
        result = await session.execute(
            select(DailyWinner).where(
                and_(
                    DailyWinner.chat_id == chat_id,
                    func.date(DailyWinner.date) == today
                )
            )
        )
        return result.scalar_one_or_none() is not None


async def select_daily_winner(chat_id: int) -> dict:
    Session = get_session()
    async with Session() as session:
        if await has_daily_winner_today(chat_id):
            return None
        
        eligible = await get_eligible_users_for_daily(chat_id)
        if not eligible:
            return None
        
        winner_chat = random.choice(eligible)
        bonus = random.randint(5, 15)
        
        winner = DailyWinner(
            chat_id=chat_id,
            telegram_id=winner_chat.telegram_id,
            date=datetime.utcnow(),
            bonus_growth=bonus
        )
        session.add(winner)
        
        uc_result = await session.execute(
            select(UserChat).where(
                and_(
                    UserChat.telegram_id == winner_chat.telegram_id,
                    UserChat.chat_id == chat_id
                )
            )
        )
        user_chat = uc_result.scalar_one_or_none()
        if user_chat:
            user_chat.length += bonus
        
        user_result = await session.execute(
            select(User).where(User.telegram_id == winner_chat.telegram_id)
        )
        user = user_result.scalar_one_or_none()
        
        await session.commit()
        
        return {
            'telegram_id': winner_chat.telegram_id,
            'username': user.username if user else None,
            'first_name': user.first_name if user else None,
            'bonus': bonus
        }


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


async def get_active_chats() -> list:
    Session = get_session()
    async with Session() as session:
        week_ago = datetime.utcnow() - timedelta(days=7)
        result = await session.execute(
            select(UserChat.chat_id)
            .where(UserChat.last_active >= week_ago)
            .distinct()
        )
        return [row[0] for row in result.all()]


async def create_pvp_challenge(chat_id: int, challenger_id: int, opponent_id: int, bet: float, opponent_username: str = None) -> PvpChallenge:
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
        
        # Allow multiple challenges - no restriction on pending challenges
        
        challenge = PvpChallenge(
            chat_id=chat_id,
            challenger_id=challenger_id,
            opponent_id=opponent_id,
            opponent_username=opponent_username.lower() if opponent_username else None,
            bet_amount=bet
        )
        session.add(challenge)
        await session.commit()
        await session.refresh(challenge)
        return challenge


async def get_pending_pvp_challenge(challenge_id: int) -> PvpChallenge:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(PvpChallenge).where(
                and_(
                    PvpChallenge.id == challenge_id,
                    PvpChallenge.status == 'pending'
                )
            )
        )
        return result.scalar_one_or_none()


async def update_pvp_opponent_id(challenge_id: int, new_opponent_id: int) -> bool:
    """Update opponent_id when a user accepts via username match."""
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(PvpChallenge).where(PvpChallenge.id == challenge_id)
        )
        challenge = result.scalar_one_or_none()
        if challenge:
            challenge.opponent_id = new_opponent_id
            await session.commit()
            return True
        return False


async def accept_pvp_challenge(challenge_id: int) -> dict:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(PvpChallenge).where(
                and_(
                    PvpChallenge.id == challenge_id,
                    PvpChallenge.status == 'pending'
                )
            )
        )
        challenge = result.scalar_one_or_none()
        if not challenge:
            return None
        
        # Check challenger still has enough (they may have lost since creating challenge)
        challenger_check = await session.execute(
            select(UserChat).where(
                and_(
                    UserChat.telegram_id == challenge.challenger_id,
                    UserChat.chat_id == challenge.chat_id
                )
            )
        )
        challenger_uc = challenger_check.scalar_one_or_none()
        if not challenger_uc or (challenger_uc.length + challenger_uc.paid_length) < challenge.bet_amount:
            return {'error': 'challenger_insufficient_funds'}
        
        # Check opponent has enough
        opponent_result = await session.execute(
            select(UserChat).where(
                and_(
                    UserChat.telegram_id == challenge.opponent_id,
                    UserChat.chat_id == challenge.chat_id
                )
            )
        )
        opponent = opponent_result.scalar_one_or_none()
        if not opponent or (opponent.length + opponent.paid_length) < challenge.bet_amount:
            return {'error': 'insufficient_funds'}
        
        challenger_roll = random.randint(1, 100)
        opponent_roll = random.randint(1, 100)
        
        if challenger_roll > opponent_roll:
            winner_id = challenge.challenger_id
            loser_id = challenge.opponent_id
        elif opponent_roll > challenger_roll:
            winner_id = challenge.opponent_id
            loser_id = challenge.challenger_id
        else:
            challenge.status = 'draw'
            await session.commit()
            return {'draw': True, 'challenger_roll': challenger_roll, 'opponent_roll': opponent_roll}
        
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
            winner_chat.pvp_wins = (winner_chat.pvp_wins or 0) + 1
            if (winner_chat.pvp_streak or 0) >= 0:
                winner_chat.pvp_streak = (winner_chat.pvp_streak or 0) + 1
            else:
                winner_chat.pvp_streak = 1
        if loser_chat:
            loser_chat.length -= challenge.bet_amount
            loser_chat.pvp_losses = (loser_chat.pvp_losses or 0) + 1
            if (loser_chat.pvp_streak or 0) <= 0:
                loser_chat.pvp_streak = (loser_chat.pvp_streak or 0) - 1
            else:
                loser_chat.pvp_streak = -1
        
        challenge.status = 'resolved'
        challenge.winner_id = winner_id
        
        await session.commit()
        
        return {
            'winner_id': winner_id,
            'loser_id': loser_id,
            'bet': challenge.bet_amount,
            'challenger_id': challenge.challenger_id,
            'opponent_id': challenge.opponent_id,
            'challenger_roll': challenger_roll,
            'opponent_roll': opponent_roll,
            'winner_streak': winner_chat.pvp_streak if winner_chat else 0,
            'loser_streak': loser_chat.pvp_streak if loser_chat else 0
        }


async def decline_pvp_challenge(challenge_id: int) -> bool:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(PvpChallenge).where(
                and_(
                    PvpChallenge.id == challenge_id,
                    PvpChallenge.status == 'pending'
                )
            )
        )
        challenge = result.scalar_one_or_none()
        if not challenge:
            return False
        
        challenge.status = 'declined'
        await session.commit()
        return True


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


async def gift_length(sender_id: int, receiver_id: int, chat_id: int, amount: float) -> dict:
    """Transfer length from one user to another in the same chat."""
    Session = get_session()
    async with Session() as session:
        # Get sender's stats
        sender_result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == sender_id, UserChat.chat_id == chat_id)
            )
        )
        sender_chat = sender_result.scalar_one_or_none()
        
        if not sender_chat:
            return {"success": False, "error": "sender_not_found"}
        
        # Calculate total length (free + paid)
        sender_total = sender_chat.length + sender_chat.paid_length
        
        if sender_total < amount:
            return {"success": False, "error": "insufficient_length", "available": sender_total}
        
        # Get receiver's stats
        receiver_result = await session.execute(
            select(UserChat).where(
                and_(UserChat.telegram_id == receiver_id, UserChat.chat_id == chat_id)
            )
        )
        receiver_chat = receiver_result.scalar_one_or_none()
        
        if not receiver_chat:
            return {"success": False, "error": "receiver_not_found"}
        
        # Deduct from sender (prioritize free length first)
        remaining_to_deduct = amount
        if sender_chat.length >= remaining_to_deduct:
            sender_chat.length -= remaining_to_deduct
        else:
            # Use all free length first, then paid length
            remaining_to_deduct -= sender_chat.length
            sender_chat.length = 0
            sender_chat.paid_length -= remaining_to_deduct
        
        # Add to receiver's free length
        receiver_chat.length += amount
        
        await session.commit()
        return {
            "success": True,
            "sender_new_total": sender_chat.length + sender_chat.paid_length,
            "receiver_new_total": receiver_chat.length + receiver_chat.paid_length
        }


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


async def get_setting(key: str) -> str | None:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(BotSettings).where(BotSettings.key == key)
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else None


async def set_setting(key: str, value: str, updated_by: int = None) -> bool:
    Session = get_session()
    async with Session() as session:
        result = await session.execute(
            select(BotSettings).where(BotSettings.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.value = value
            setting.updated_by = updated_by
            setting.updated_at = datetime.utcnow()
        else:
            setting = BotSettings(key=key, value=value, updated_by=updated_by)
            session.add(setting)
        
        await session.commit()
        return True


async def get_team_wallet() -> str | None:
    return await get_setting('team_wallet_address')


async def get_package_price(package_num: int, default_price: int) -> int:
    """Get package price from database or return default."""
    price_str = await get_setting(f'package_{package_num}_price')
    if price_str:
        try:
            return int(price_str)
        except ValueError:
            pass
    return default_price


async def set_package_price(package_num: int, price: int, updated_by: int = None) -> bool:
    """Set package price in database."""
    return await set_setting(f'package_{package_num}_price', str(price), updated_by)


async def get_package_growth(package_num: int, default_growth: int) -> int:
    """Get package growth from database or return default."""
    growth_str = await get_setting(f'package_{package_num}_growth')
    if growth_str:
        try:
            return int(growth_str)
        except ValueError:
            pass
    return default_growth


async def set_package_growth(package_num: int, growth: int, updated_by: int = None) -> bool:
    """Set package growth in database."""
    return await set_setting(f'package_{package_num}_growth', str(growth), updated_by)
