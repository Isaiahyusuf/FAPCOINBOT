import os
import base64
from typing import Optional, Tuple
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def get_encryption_key() -> bytes:
    secret = os.environ.get('WALLET_ENCRYPTION_KEY', 'default-key-change-in-production')
    salt = os.environ.get('WALLET_SALT', 'fapcoin-salt').encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode()))


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


FEE_WINNER = 0.98
FEE_TREASURY = 0.01
FEE_GROUP_OWNER = 0.01
FEE_DEV = 0.00

def calculate_bet_distribution(total_pot: float) -> dict:
    winner_amount = total_pot * FEE_WINNER
    treasury_amount = total_pot * FEE_TREASURY
    group_owner_amount = total_pot * FEE_GROUP_OWNER
    dev_amount = total_pot * FEE_DEV
    
    return {
        'winner': winner_amount,
        'treasury': treasury_amount,
        'group_owner': group_owner_amount,
        'dev': dev_amount
    }
