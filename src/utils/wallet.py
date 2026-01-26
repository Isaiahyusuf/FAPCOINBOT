import os
import base64
import logging
from typing import Optional, Tuple
from decimal import Decimal, ROUND_DOWN
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

_cached_encryption_key = None

def get_encryption_key() -> bytes:
    global _cached_encryption_key
    if _cached_encryption_key:
        return _cached_encryption_key
    
    key = os.environ.get('ENCRYPTION_KEY')
    if key:
        if len(key) == 44 and key.endswith('='):
            _cached_encryption_key = key.encode()
            return _cached_encryption_key
        salt = os.environ.get('WALLET_SALT', os.environ.get('REPL_ID', 'production-salt')).encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        _cached_encryption_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        return _cached_encryption_key
    
    logger.warning("ENCRYPTION_KEY not set! Using auto-generated key. Wallets will be LOST on restart!")
    _cached_encryption_key = Fernet.generate_key()
    return _cached_encryption_key


def generate_wallet() -> Tuple[str, str]:
    keypair = Keypair()
    public_key = str(keypair.pubkey())
    private_key_bytes = bytes(keypair)
    
    fernet = Fernet(get_encryption_key())
    encrypted_private_key = fernet.encrypt(private_key_bytes).decode()
    
    return public_key, encrypted_private_key


def decrypt_private_key(encrypted_private_key: str) -> Keypair:
    fernet = Fernet(get_encryption_key())
    private_key_bytes = fernet.decrypt(encrypted_private_key.encode())
    return Keypair.from_bytes(private_key_bytes)


def validate_solana_address(address: str) -> bool:
    try:
        Pubkey.from_string(address)
        return True
    except:
        return False


FEE_WINNER = Decimal('0.98')
FEE_TREASURY = Decimal('0.01')
FEE_GROUP_OWNER = Decimal('0.01')
FEE_DEV = Decimal('0.00')

MAIN_FAPCOIN_GROUP = int(os.environ.get('MAIN_FAPCOIN_GROUP', '0'))

def is_main_fapcoin_group(chat_id: int) -> bool:
    """Check if the chat is the main FAPCOIN group."""
    return chat_id == MAIN_FAPCOIN_GROUP


def get_bot_treasury_wallet() -> Optional[Tuple[str, Keypair]]:
    """Get the bot's treasury wallet from environment.
    Returns (public_key, keypair) or None if not configured."""
    private_key_base64 = os.environ.get('BOT_TREASURY_PRIVATE_KEY')
    if not private_key_base64:
        return None
    
    try:
        private_key_bytes = base64.b64decode(private_key_base64)
        keypair = Keypair.from_bytes(private_key_bytes)
        public_key = str(keypair.pubkey())
        return (public_key, keypair)
    except Exception as e:
        logger.error(f"Failed to load bot treasury wallet: {e}")
        return None


def generate_bot_treasury_wallet() -> Tuple[str, str]:
    """Generate a new bot treasury wallet.
    Returns (public_key, base64_private_key) for storage in environment."""
    keypair = Keypair()
    public_key = str(keypair.pubkey())
    private_key_base64 = base64.b64encode(bytes(keypair)).decode()
    return public_key, private_key_base64


def calculate_bet_distribution(total_pot: float, is_main_group: bool = False) -> dict:
    """Calculate bet distribution.
    For main FAPCOIN group: 98% winner, 2% treasury (no group owner cut)
    For other groups: 98% winner, 1% treasury, 1% group owner
    """
    pot = Decimal(str(total_pot))
    
    if is_main_group:
        treasury_amount = (pot * Decimal('0.02')).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        group_owner_amount = Decimal('0')
    else:
        treasury_amount = (pot * FEE_TREASURY).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        group_owner_amount = (pot * FEE_GROUP_OWNER).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    dev_amount = (pot * FEE_DEV).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    winner_amount = pot - treasury_amount - group_owner_amount - dev_amount
    
    return {
        'winner': float(winner_amount),
        'treasury': float(treasury_amount),
        'group_owner': float(group_owner_amount),
        'dev': float(dev_amount)
    }
