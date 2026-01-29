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


def generate_wallet(telegram_id: int) -> Tuple[str, str]:
    """Generate a permanent wallet using Telegram ID as a seed for consistent keys if needed, 
    though here we just generate and the caller handles storage by Telegram ID."""
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


def get_main_wallet() -> Optional[Tuple[str, Keypair]]:
    """Get the main wallet from environment for signing transactions.
    Returns (public_key, keypair) or None if not configured."""
    address = os.environ.get('MAIN_WALLET_ADDRESS')
    private_key = os.environ.get('MAIN_WALLET_PRIVATE_KEY')
    
    if not address or not private_key:
        logger.warning("MAIN_WALLET not configured - on-chain transfers disabled")
        return None
    
    try:
        import base58
        private_key_bytes = base58.b58decode(private_key)
        keypair = Keypair.from_bytes(private_key_bytes)
        loaded_address = str(keypair.pubkey())
        
        if loaded_address != address:
            logger.error(f"Main wallet address mismatch! Expected {address}, got {loaded_address}")
            return None
        
        logger.info(f"Main wallet loaded: {address[:8]}...{address[-4:]}")
        return (address, keypair)
    except Exception as e:
        logger.error(f"Failed to load main wallet: {e}")
        return None


def get_main_wallet_address() -> Optional[str]:
    """Get just the main wallet address without loading private key."""
    return os.environ.get('MAIN_WALLET_ADDRESS')


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


FAPCOIN_MINT = os.environ.get('FAPCOIN_MINT', '')
FAPCOIN_DECIMALS = 6

SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
TOKEN_PROGRAM_ID_STR = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ASSOCIATED_TOKEN_PROGRAM_ID_STR = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"


async def get_token_balance(wallet_address: str, mint_address: str = None) -> float:
    """Get FAPCOIN token balance for a wallet address."""
    import aiohttp
    
    if mint_address is None:
        mint_address = FAPCOIN_MINT
    
    if not mint_address:
        return 0.0
    
    rpc_url = os.environ.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
    
    try:
        from solders.pubkey import Pubkey as SoldersPubkey
        
        owner_pubkey = SoldersPubkey.from_string(wallet_address)
        mint_pubkey = SoldersPubkey.from_string(mint_address)
        token_program = SoldersPubkey.from_string(TOKEN_PROGRAM_ID_STR)
        ata_program = SoldersPubkey.from_string(ASSOCIATED_TOKEN_PROGRAM_ID_STR)
        
        seeds = [bytes(owner_pubkey), bytes(token_program), bytes(mint_pubkey)]
        ata_address, _ = SoldersPubkey.find_program_address(seeds, ata_program)
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountBalance",
                "params": [str(ata_address)]
            }
            async with session.post(rpc_url, json=payload) as resp:
                result = await resp.json()
                if "error" in result or result.get("result", {}).get("value") is None:
                    return 0.0
                ui_amount = result["result"]["value"].get("uiAmount", 0)
                return float(ui_amount) if ui_amount else 0.0
    except Exception as e:
        logger.error(f"Error getting token balance: {e}")
        return 0.0


async def get_sol_balance(wallet_address: str) -> float:
    """Get SOL balance for a wallet address."""
    import aiohttp
    
    rpc_url = os.environ.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [wallet_address]
            }
            async with session.post(rpc_url, json=payload) as resp:
                result = await resp.json()
                if "error" in result:
                    return 0.0
                lamports = result.get("result", {}).get("value", 0)
                return lamports / 1_000_000_000
    except Exception as e:
        logger.error(f"Error getting SOL balance: {e}")
        return 0.0


async def check_transaction_status(tx_signature: str) -> Tuple[str, Optional[str]]:
    """Check transaction status on Solana.
    
    Returns: (status, error_message)
    status can be: 'confirmed', 'finalized', 'pending', 'failed'
    """
    import aiohttp
    import asyncio
    
    rpc_url = os.environ.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignatureStatuses",
                "params": [[tx_signature], {"searchTransactionHistory": True}]
            }
            async with session.post(rpc_url, json=payload) as resp:
                result = await resp.json()
                
                if "error" in result:
                    return "failed", f"RPC error: {result['error']}"
                
                statuses = result.get("result", {}).get("value", [])
                if not statuses or statuses[0] is None:
                    return "pending", None
                
                status = statuses[0]
                if status.get("err"):
                    return "failed", f"Transaction error: {status['err']}"
                
                confirmation_status = status.get("confirmationStatus", "")
                if confirmation_status in ["confirmed", "finalized"]:
                    return confirmation_status, None
                
                return "pending", None
    except Exception as e:
        logger.error(f"Error checking tx status: {e}")
        return "failed", str(e)


async def send_fapcoin_with_retry(to_address: str, amount: float, max_retries: int = 3, check_delay: float = 5.0) -> Tuple[bool, Optional[str], Optional[str]]:
    """Send FAPCOIN with automatic retry and confirmation checking.
    
    Returns: (success, tx_signature, error_message)
    """
    import asyncio
    
    last_error = None
    
    for attempt in range(max_retries):
        if attempt > 0:
            logger.info(f"Retry attempt {attempt + 1}/{max_retries} for FAPCOIN transfer to {to_address}")
        
        success, tx_signature, error = await send_fapcoin(to_address, amount)
        
        if not success:
            last_error = error
            if "Insufficient" in (error or ""):
                return False, None, error
            await asyncio.sleep(2)
            continue
        
        await asyncio.sleep(check_delay)
        
        status, status_error = await check_transaction_status(tx_signature)
        
        if status in ["confirmed", "finalized"]:
            logger.info(f"Transaction {tx_signature} confirmed on attempt {attempt + 1}")
            return True, tx_signature, None
        elif status == "failed":
            last_error = status_error or "Transaction failed on-chain"
            logger.warning(f"Transaction {tx_signature} failed: {last_error}")
            continue
        else:
            for _ in range(3):
                await asyncio.sleep(3)
                status, status_error = await check_transaction_status(tx_signature)
                if status in ["confirmed", "finalized"]:
                    logger.info(f"Transaction {tx_signature} confirmed after additional wait")
                    return True, tx_signature, None
                elif status == "failed":
                    break
            
            if status in ["confirmed", "finalized"]:
                return True, tx_signature, None
            elif status == "failed":
                last_error = status_error or "Transaction failed on-chain"
            else:
                return True, tx_signature, None
    
    return False, None, last_error or "Transaction failed after all retries"


async def send_fapcoin(to_address: str, amount: float) -> Tuple[bool, Optional[str], Optional[str]]:
    """Send FAPCOIN tokens from main wallet to destination.
    
    Professional-grade SPL token transfer with:
    - Compute budget for priority fees
    - Fresh blockhash for each attempt
    - Proper ATA creation
    - Transaction confirmation waiting
    
    Returns: (success, tx_signature, error_message)
    """
    import aiohttp
    import struct
    import asyncio
    
    main_wallet = get_main_wallet()
    if not main_wallet:
        return False, None, "Main wallet not configured"
    
    main_address, main_keypair = main_wallet
    rpc_url = os.environ.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
    
    if not FAPCOIN_MINT:
        return False, None, "FAPCOIN_MINT not configured"
    
    if not validate_solana_address(to_address):
        return False, None, "Invalid destination address"
    
    sol_balance = await get_sol_balance(main_address)
    if sol_balance < 0.005:
        return False, None, f"Insufficient SOL for gas fees (have {sol_balance:.4f} SOL, need 0.005)"
    
    token_balance = await get_token_balance(main_address)
    if token_balance < amount:
        return False, None, f"Insufficient FAPCOIN in main wallet (have {token_balance:,.2f}, need {amount:,.2f})"
    
    try:
        raw_amount = int(amount * (10 ** FAPCOIN_DECIMALS))
        
        from solders.pubkey import Pubkey as SoldersPubkey
        from solders.transaction import Transaction
        from solders.message import Message
        from solders.instruction import Instruction, AccountMeta
        from solders.hash import Hash
        
        mint_pubkey = SoldersPubkey.from_string(FAPCOIN_MINT)
        owner_pubkey = main_keypair.pubkey()
        dest_pubkey = SoldersPubkey.from_string(to_address)
        
        TOKEN_PROGRAM_ID = SoldersPubkey.from_string(TOKEN_PROGRAM_ID_STR)
        ASSOCIATED_TOKEN_PROGRAM_ID = SoldersPubkey.from_string(ASSOCIATED_TOKEN_PROGRAM_ID_STR)
        SYSTEM_PROGRAM = SoldersPubkey.from_string(SYSTEM_PROGRAM_ID)
        COMPUTE_BUDGET_PROGRAM = SoldersPubkey.from_string("ComputeBudget111111111111111111111111111111")
        
        def get_associated_token_address(owner: SoldersPubkey, mint: SoldersPubkey) -> SoldersPubkey:
            seeds = [bytes(owner), bytes(TOKEN_PROGRAM_ID), bytes(mint)]
            program_address, _ = SoldersPubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM_ID)
            return program_address
        
        source_ata = get_associated_token_address(owner_pubkey, mint_pubkey)
        dest_ata = get_associated_token_address(dest_pubkey, mint_pubkey)
        
        async with aiohttp.ClientSession() as session:
            blockhash_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getLatestBlockhash",
                "params": [{"commitment": "confirmed"}]
            }
            async with session.post(rpc_url, json=blockhash_payload) as resp:
                result = await resp.json()
                if "error" in result:
                    return False, None, f"RPC error getting blockhash: {result['error']}"
                blockhash_str = result["result"]["value"]["blockhash"]
                last_valid_block = result["result"]["value"]["lastValidBlockHeight"]
            
            check_ata_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [str(dest_ata), {"encoding": "base64"}]
            }
            async with session.post(rpc_url, json=check_ata_payload) as resp:
                ata_result = await resp.json()
                dest_ata_exists = ata_result.get("result", {}).get("value") is not None
        
        instructions = []
        
        set_compute_limit_data = bytes([2]) + struct.pack('<I', 200000)
        set_compute_limit_ix = Instruction(COMPUTE_BUDGET_PROGRAM, set_compute_limit_data, [])
        instructions.append(set_compute_limit_ix)
        
        set_priority_fee_data = bytes([3]) + struct.pack('<Q', 50000)
        set_priority_fee_ix = Instruction(COMPUTE_BUDGET_PROGRAM, set_priority_fee_data, [])
        instructions.append(set_priority_fee_ix)
        
        if not dest_ata_exists:
            create_ata_accounts = [
                AccountMeta(owner_pubkey, is_signer=True, is_writable=True),
                AccountMeta(dest_ata, is_signer=False, is_writable=True),
                AccountMeta(dest_pubkey, is_signer=False, is_writable=False),
                AccountMeta(mint_pubkey, is_signer=False, is_writable=False),
                AccountMeta(SYSTEM_PROGRAM, is_signer=False, is_writable=False),
                AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            ]
            create_ata_ix = Instruction(ASSOCIATED_TOKEN_PROGRAM_ID, bytes(), create_ata_accounts)
            instructions.append(create_ata_ix)
            logger.info(f"Creating ATA for destination: {dest_ata}")
        
        transfer_data = bytes([3]) + struct.pack('<Q', raw_amount)
        transfer_accounts = [
            AccountMeta(source_ata, is_signer=False, is_writable=True),
            AccountMeta(dest_ata, is_signer=False, is_writable=True),
            AccountMeta(owner_pubkey, is_signer=True, is_writable=False),
        ]
        transfer_ix = Instruction(TOKEN_PROGRAM_ID, transfer_data, transfer_accounts)
        instructions.append(transfer_ix)
        
        blockhash = Hash.from_string(blockhash_str)
        message = Message.new_with_blockhash(instructions, owner_pubkey, blockhash)
        tx = Transaction.new_unsigned(message)
        tx.sign([main_keypair], blockhash)
        
        tx_bytes = bytes(tx)
        tx_base64 = base64.b64encode(tx_bytes).decode('utf-8')
        
        async with aiohttp.ClientSession() as session:
            sim_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "simulateTransaction",
                "params": [tx_base64, {"encoding": "base64", "commitment": "confirmed"}]
            }
            async with session.post(rpc_url, json=sim_payload) as resp:
                sim_result = await resp.json()
                if "error" in sim_result:
                    return False, None, f"Simulation error: {sim_result['error']}"
                sim_value = sim_result.get("result", {}).get("value", {})
                if sim_value.get("err"):
                    return False, None, f"Simulation failed: {sim_value['err']}"
            
            send_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendTransaction",
                "params": [tx_base64, {
                    "encoding": "base64",
                    "skipPreflight": True,
                    "preflightCommitment": "confirmed",
                    "maxRetries": 3
                }]
            }
            async with session.post(rpc_url, json=send_payload) as resp:
                send_result = await resp.json()
                if "error" in send_result:
                    error_msg = send_result['error'].get('message', str(send_result['error']))
                    logger.error(f"Transaction send error: {error_msg}")
                    return False, None, f"Transaction failed: {error_msg}"
                tx_signature = send_result["result"]
            
            logger.info(f"Transaction sent: {tx_signature}, waiting for confirmation...")
            
            for i in range(30):
                await asyncio.sleep(2)
                
                status_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignatureStatuses",
                    "params": [[tx_signature], {"searchTransactionHistory": True}]
                }
                async with session.post(rpc_url, json=status_payload) as resp:
                    status_result = await resp.json()
                    statuses = status_result.get("result", {}).get("value", [])
                    
                    if statuses and statuses[0]:
                        status = statuses[0]
                        if status.get("err"):
                            return False, tx_signature, f"Transaction failed on-chain: {status['err']}"
                        
                        confirmation = status.get("confirmationStatus", "")
                        if confirmation in ["confirmed", "finalized"]:
                            logger.info(f"FAPCOIN transfer confirmed: {tx_signature} - {amount} FAPCOIN to {to_address}")
                            return True, tx_signature, None
                
                block_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBlockHeight",
                    "params": []
                }
                async with session.post(rpc_url, json=block_payload) as resp:
                    block_result = await resp.json()
                    current_block = block_result.get("result", 0)
                    if current_block > last_valid_block:
                        return False, None, "Transaction expired (blockhash too old)"
            
            return False, tx_signature, "Transaction sent but confirmation timed out"
                
    except Exception as e:
        logger.error(f"FAPCOIN transfer error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, None, str(e)
