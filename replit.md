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

## Required Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `TEAM_WALLET_ADDRESS` | Solana wallet for receiving FAPCOIN | Yes |
| `SOLANA_RPC_URL` | Solana RPC endpoint | Yes |

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
- `/wallet <address>` - Register Solana wallet
- `/buy <package>` - View and purchase growth packages
- `/verify <tx_hash>` - Verify Solana transaction on-chain
- Package prices: 5k-25k FAPCOIN for 20-100 cm growth
- Double-spend protection (same tx can't be used twice)

### Support
- `/support` - Create support ticket with contact username

## Database Models
- User: Telegram user info and Solana wallet
- UserChat: Per-chat stats (length, paid_length, debt, last_grow)
- Transaction: FAPCOIN purchase records (pending/confirmed)
- DailyWinner: Daily winner records per chat
- PvpChallenge: PvP betting records (pending/resolved/declined)
- SupportRequest: Support ticket tracking
