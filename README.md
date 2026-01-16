# FAPCOINBOT

FAPCOIN DICK BOT — Full README

Overview:

FAPCOIN DICK BOT is a competitive Telegram game bot where users can grow their “length,” compete on leaderboards, challenge friends in PvP, and optionally purchase growth using $FAPCOIN on Solana. The bot is privacy-first, spam-free, and designed for fun, monetizable gameplay.

All sensitive data (tokens, wallet addresses, RPC endpoints, database URLs) must be stored in Railway Secret Environment.

⸻

Features:
	1.	Daily Growth
Users can use the command /grow once per day in each chat. Each growth is random between -5 and +20 cm. Users with negative value (debt) receive a 0.2% bonus per growth. Users can also use /loan to reset their value to zero while creating a repayment debt.
	2.	Leaderboard
The command /top displays the top users in the current chat. Rankings include both free and paid growth.
	3.	Daily Election – “Dick of the Day”
Each chat automatically selects a winner daily. Eligibility requires the user to have used /grow at least once in the past 7 days. The winner receives bonus growth automatically.
	4.	PvP Betting
The command /pvp <@user>  allows users to challenge others to wager growth points. The winner receives the bet amount and the loser loses it. Users must have sufficient points to participate.
	5.	Inline Mode
The bot can be used without adding it to a chat. Use inline queries by typing @BotUsername followed by the command. Inline commands include /grow, /top, /pvp, /loan, /wallet, /buy, /support.
	6.	Loan System
The command /loan resets negative value to zero and creates a repayment debt that is repaid gradually with future growth.
	7.	Paid Growth – $FAPCOIN Integration
Users can register their Solana wallet using /wallet <SOL_ADDRESS>.
Users can buy growth packages using /buy <package_number>. Available packages:

Package 1: 20 cm growth for 5,000 FAPCOIN
Package 2: 40 cm growth for 10,000 FAPCOIN
Package 3: 60 cm growth for 15,000 FAPCOIN
Package 4: 80 cm growth for 20,000 FAPCOIN
Package 5: 100 cm growth for 25,000 FAPCOIN

Payments go directly to TEAM_WALLET. The bot verifies on-chain transactions before crediting user growth.
	8.	Support
Users who need assistance can use the command /support. The bot will ask the user to provide a support username, which the admin or team can respond to directly.

⸻

Commands:

/grow – Daily random growth
/top – Show chat leaderboard
/pvp <@user>  – Challenge a user with a wager
/loan – Reset debt to zero
/wallet <SOL_ADDRESS> – Register Solana wallet
/buy <package_number> – Purchase growth with $FAPCOIN
/support – Request support by providing a support username

⸻

Database / Storage:

User data includes Telegram user ID, chat ID, total length (free + paid), debt (if /loan is used), and wallet address (optional).
Transactions store transaction ID, user ID, amount paid, package number, and status (pending or confirmed).
Leaderboards store chat ID, user ID, and total length.

⸻

Railway Secret Environment Variables (must be set):

BOT_TOKEN – Telegram bot token
TEAM_WALLET_ADDRESS – Solana wallet for payments
SOLANA_RPC_URL – RPC endpoint for Solana transactions
DATABASE_URL – SQLite or Postgres connection string

Important: Do NOT hardcode any of these values in the code. Always store them as secrets in Railway.

⸻

Deployment Instructions:
	1.	Clone the repository.
	2.	Install dependencies (for Python + Aiogram: pip install -r requirements.txt).
	3.	Set all environment variables in Railway Secret Environment.
	4.	Run the bot (python main.py).
	5.	Optional: Add bot to chat or use inline mode.
	6.	Test commands: /grow, /top, /wallet, /buy, /pvp, /support.

⸻

Security & Privacy:

Privacy mode is enabled by default. The bot cannot read all messages. There are no ads or spam. Only public wallet addresses are used for $FAPCOIN purchases. Transactions are verified directly on-chain. No private keys are stored.

⸻

Support:

Use the /support command to provide a support username. Admins or team members can respond to support requests directly in Telegram.
