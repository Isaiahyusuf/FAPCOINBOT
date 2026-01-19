# FAPCOIN DICK BOT

## Overview
A competitive Telegram game bot where users can grow their "length," compete on leaderboards, challenge friends in PvP, and optionally purchase growth using $FAPCOIN on Solana.

## Project Structure
```
.
├── main.py                    # Bot entry point
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

## Required Environment Variables
- `BOT_TOKEN` - Telegram bot token (required to run)
- `TEAM_WALLET_ADDRESS` - Solana wallet for receiving FAPCOIN payments
- `SOLANA_RPC_URL` - RPC endpoint for Solana transactions (optional)
- `DATABASE_URL` - Automatically provided by Replit PostgreSQL

## Bot Commands
- `/start` - Welcome message and commands list
- `/grow` - Daily random growth (-5 to +20 cm)
- `/top` - Show chat leaderboard
- `/pvp @user <bet>` - Challenge a user with a wager
- `/loan` - Reset debt to zero (creates repayment debt)
- `/wallet <address>` - Register Solana wallet
- `/buy <package>` - Purchase growth with $FAPCOIN
- `/support` - Request support

## Database Models
- User: Telegram user info and wallet
- UserChat: Per-chat user stats (length, debt, etc.)
- Transaction: FAPCOIN purchase records
- DailyWinner: Daily "Dick of the Day" winners
- PvpChallenge: PvP betting records
- SupportRequest: Support ticket tracking

## Running the Bot
1. Set the `BOT_TOKEN` secret with your Telegram bot token
2. Optionally set `TEAM_WALLET_ADDRESS` for payment processing
3. The workflow will automatically start the bot
