# FAPCOIN DICK BOT

## Overview
A competitive Telegram game bot where users can grow their "length," compete on leaderboards, challenge friends in PvP, and bet real FAPCOIN tokens against each other using $FAPCOIN on Solana.

## Project Structure
```
.
├── main.py                    # Bot entry point with daily winner scheduler
├── src/
│   ├── database/
│   │   ├── models.py          # SQLAlchemy models (User, UserWallet, FapcoinBet, etc.)
│   │   └── db.py              # Database operations
│   ├── handlers/
│   │   └── commands.py        # Telegram command handlers
│   └── utils/
│       └── wallet.py          # Solana wallet utilities (keypair generation, encryption)
├── requirements.txt           # Python dependencies for Railway
├── Procfile                   # Railway process file
├── railway.toml               # Railway config
└── README.md                  # Original project documentation
```

## Tech Stack
- Python 3.11+
- aiogram 3.x (Telegram Bot API)
- SQLAlchemy with asyncpg (PostgreSQL async driver)
- PostgreSQL database
- aiohttp for Solana RPC calls
- solana/solders for Solana keypair management
- cryptography for wallet private key encryption

## Required Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `TEAM_WALLET_ADDRESS` | Solana wallet for receiving FAPCOIN | Yes |
| `SOLANA_RPC_URL` | Solana RPC endpoint | Yes |
| `TREASURY_WALLET` | Treasury wallet for betting fees (1%) | Yes |
| `DEV_WALLET` | Developer wallet for fees (0%) | No |
| `ENCRYPTION_KEY` | Fernet key for wallet encryption | Auto-generated |

## Railway Deployment

1. Push code to GitHub
2. Connect Railway to your GitHub repo
3. Add a PostgreSQL database in Railway
4. Set environment variables in Railway:
   - `BOT_TOKEN` - Your Telegram bot token
   - `DATABASE_URL` - Auto-provided when you add PostgreSQL
   - `TEAM_WALLET_ADDRESS` - Your Solana wallet address
   - `SOLANA_RPC_URL` - e.g., `https://api.mainnet-beta.solana.com`
5. Deploy!

## Implemented Features

### Core Gameplay
- `/grow` - Daily random growth (-5 to +20 cm), once per day per chat
- `/top` - Chat leaderboard showing top 10 players
- `/gift` - Gift cm to another user (reply + /gift [amount])
- `/loan` - Reset negative length to zero, creating repayment debt
- `/help` - Show all commands
- Debt bonus: Users with negative length get 0.2% bonus per growth
- Debt repayment: 20% of positive growth goes to debt repayment

### Group Support
- Bot works in any group when added with admin rights
- Each group has its own separate leaderboard
- Auto-welcome message when bot joins a group

### Daily Election - "Dick of the Day"
- `/daily` - Manually trigger daily winner selection
- Automatic selection runs at 12:00 UTC daily
- Eligibility: Users who used /grow in the past 7 days
- Winner receives random 5-15 cm bonus

### PvP Betting
- `/pvp @user <bet>` - Challenge a user with length wager
- Accept/Decline buttons for the challenged user
- Random dice roll determines winner
- Winner gains bet amount, loser loses bet amount

### FAPCOIN Integration
- `/wallet <address>` - Register Solana wallet for purchases
- `/buy <package>` - View and purchase growth packages
- `/verify <tx_hash>` - Verify Solana transaction on-chain
- Package prices: 5k-25k FAPCOIN for 20-100 cm growth
- Double-spend protection (same tx can't be used twice)

### FAPCOIN Betting System
- `/wallet` - View your burner wallet (auto-generated) with deposit address and balance
- `/deposit` - Check for new deposits and view current balance
- `/withdraw [amount] [address]` - Withdraw FAPCOIN to a Solana address (min: 500 FAPCOIN)
- `/fapbet [amount] @user` - Challenge another user to a FAPCOIN bet (min: 100, max: 10,000 FAPCOIN)
- `/setgroupwallet [address]` - Group admins only can set wallet to receive 1% of bets
- `/betstats` - View betting statistics for group and global
- Inline buttons: Check Deposit, Withdraw, Back to Wallet
- Accept/Decline buttons for bet challenges
- Random dice roll (1-100) determines winner
- Duplicate pending bet prevention
- **Wallet deletion prompt after bets** - users can delete burner wallets after each bet
- **Purchases require group context** - /buy must be used in groups (adds length to group leaderboard)
- **Betting Limits:** Min 100, Max 10,000 FAPCOIN per bet
- **Withdrawal Limit:** Min 500 FAPCOIN
- **Gas Fees:** Users must deposit ~$1 SOL to cover Solana network fees for withdrawals
- **Fee Distribution:**
  - 98% goes to winner
  - 1% goes to team wallet (TREASURY_WALLET)
  - 1% goes to group owner wallet (incentivizes groups to use the bot)
- **Security Features:**
  - Row-level database locking prevents race conditions
  - Decimal precision for fee calculations (no floating-point drift)
  - Encrypted private keys with Fernet (requires ENCRYPTION_KEY)
  - Duplicate bet prevention between same users
- **Viral Marketing:**
  - All bet messages include "$FAPCOIN on Solana" branding
  - Group owners earn 1% of all bets, encouraging bot adoption
  - Global stats show total FAPCOIN volume across all groups

### Support
- `/support` - Create support ticket with contact username

## Database Models
- User: Telegram user info and Solana wallet (for purchases)
- UserChat: Per-chat stats (length, paid_length, debt, last_grow)
- Transaction: FAPCOIN purchase records (pending/confirmed)
- DailyWinner: Daily winner records per chat
- PvpChallenge: PvP betting records (pending/resolved/declined)
- SupportRequest: Support ticket tracking
- **UserWallet (NEW)**: Burner wallet with encrypted private key, balance
- **FapcoinBet (NEW)**: Betting records with challenger, opponent, amounts, fees
- **GroupOwnerWallet (NEW)**: Group owner wallet addresses for fee payouts
