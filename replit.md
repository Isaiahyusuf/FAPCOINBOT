# FAPCOIN DICK BOT

## Overview
A competitive Telegram game bot where users can grow their "length," compete on leaderboards, challenge friends in PvP, and optionally purchase growth using $FAPCOIN on Solana.

## Project Structure
```
.
├── main.py                    # Bot entry point with daily winner scheduler
├── src/
│   ├── database/
│   │   ├── models.py          # SQLAlchemy models
│   │   └── db.py              # Database operations
│   └── handlers/
│       └── commands.py        # Telegram command handlers
├── pyproject.toml             # Python dependencies
└── README.md                  # Original project documentation
```

## Tech Stack
- Python 3.11
- aiogram 3.x (Telegram Bot API)
- SQLAlchemy with asyncpg (PostgreSQL async driver)
- PostgreSQL database (Replit built-in)
- aiohttp for Solana RPC calls

## Required Environment Variables
- `BOT_TOKEN` - Telegram bot token (REQUIRED)
- `TEAM_WALLET_ADDRESS` - Solana wallet for receiving FAPCOIN payments
- `SOLANA_RPC_URL` - RPC endpoint for Solana transaction verification
- `DATABASE_URL` - Automatically provided by Replit PostgreSQL

## Implemented Features

### Core Gameplay
- `/grow` - Daily random growth (-5 to +20 cm), once per day per chat
- `/top` - Chat leaderboard showing top 10 players
- `/loan` - Reset negative length to zero, creating repayment debt
- Debt bonus: Users with negative length get 0.2% bonus per growth
- Debt repayment: 20% of positive growth goes to debt repayment

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
- `/wallet <address>` - Register Solana wallet
- `/buy <package>` - View and purchase growth packages
- `/verify <tx_hash>` - Verify Solana transaction
- Package prices: 5k-25k FAPCOIN for 20-100 cm growth

### Support
- `/support` - Create support ticket with contact username

## Database Models
- User: Telegram user info and Solana wallet
- UserChat: Per-chat stats (length, paid_length, debt, last_grow)
- Transaction: FAPCOIN purchase records (pending/confirmed)
- DailyWinner: Daily winner records per chat
- PvpChallenge: PvP betting records (pending/resolved/declined)
- SupportRequest: Support ticket tracking

## Running the Bot
1. Set the `BOT_TOKEN` secret with your Telegram bot token
2. Set `TEAM_WALLET_ADDRESS` for payment receiving wallet
3. Set `SOLANA_RPC_URL` for transaction verification
4. The workflow will automatically start the bot
