from pymongo import MongoClient
from datetime import datetime
import argparse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
FEE_RATE = 0.001  # Trading fee rate
REQUIRED_ENV_VARS = [
    "MONGO_INITDB_ROOT_USERNAME",
    "MONGO_INITDB_ROOT_PASSWORD",
    "MONGO_HOST",
    "MONGO_PORT",
    "MONGO_INITDB_DATABASE"
]

# Check environment variables
for var in REQUIRED_ENV_VARS:
    if not os.getenv(var):
        raise EnvironmentError(f"Missing required environment variable: {var}")

DB_URI = (
    f"mongodb://{os.getenv('MONGO_INITDB_ROOT_USERNAME')}:{os.getenv('MONGO_INITDB_ROOT_PASSWORD')}"
    f"@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}/{os.getenv('MONGO_INITDB_DATABASE')}"
)
DB_NAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "trading_bot")


class PortfolioManager:
    def __init__(self, db_uri=DB_URI):
        self.mongo_client = MongoClient(db_uri)
        self.db = self.mongo_client[DB_NAME]
        self.portfolio_id = self._init_or_get_portfolio_id()

    def _init_or_get_portfolio_id(self):
        portfolio = self.db.portfolios.find_one({"active": True})
        if portfolio:
            return portfolio["_id"]
        new_portfolio = {
            "initial_balance_eur": 0,
            "balance_eur": 0,
            "holdings": {},
            "active": True,
            "created_at": datetime.now()
        }
        return self.db.portfolios.insert_one(new_portfolio).inserted_id

    def _update_portfolio(self, updates: dict):
        self.db.portfolios.update_one(
            {"_id": self.portfolio_id},
            {"$set": updates}
        )

    def _insert_transaction(self, transaction: dict):
        transaction["portfolio_id"] = self.portfolio_id
        transaction["timestamp"] = datetime.now()
        self.db.transactions.insert_one(transaction)

    def deposit_funds(self, amount_eur):
        portfolio = self.get_portfolio()
        new_balance = portfolio["balance_eur"] + amount_eur
        self._update_portfolio({"balance_eur": new_balance})
        self._insert_transaction({
            "type": "DEPOSIT",
            "amount_eur": amount_eur,
            "balance_after": new_balance
        })
        print(f"Deposited €{amount_eur:.2f}. New balance: €{new_balance:.2f}")

    def withdraw_funds(self, amount_eur):
        portfolio = self.get_portfolio()
        balance = portfolio["balance_eur"]
        if balance < amount_eur:
            print(f"❌ Insufficient balance. Available: €{balance:.2f}")
            return False

        new_balance = balance - amount_eur
        self._update_portfolio({"balance_eur": new_balance})
        self._insert_transaction({
            "type": "WITHDRAWAL",
            "amount_eur": amount_eur,
            "balance_after": new_balance
        })
        print(f"Withdrew €{amount_eur:.2f}. New balance: €{new_balance:.2f}")
        return True

    def get_portfolio(self):
        return self.db.portfolios.find_one({"_id": self.portfolio_id})

    def manual_buy(self, symbol, amount_eur=None, amount_crypto=None, price=None, fee_rate=FEE_RATE):
        """Manually record a buy transaction"""
        portfolio = self.get_portfolio()

        if price is None:
            print("Error: You must specify the price")
            return False

        if amount_eur is None and amount_crypto is None:
            print("Error: You must specify either amount_eur or amount_crypto")
            return False

        # Calculate the missing value
        if amount_eur is None:
            amount_eur = amount_crypto * price
        elif amount_crypto is None:
            amount_crypto = amount_eur / price

        fee = amount_eur * fee_rate

        # Validate sufficient balance
        if portfolio["balance_eur"] < (amount_eur + fee):
            print(f"Error: Insufficient balance. Need €{amount_eur + fee}, have €{portfolio['balance_eur']}")
            return False

        # Update balance and holdings
        new_balance = portfolio["balance_eur"] - (amount_eur + fee)
        holdings = portfolio.get("holdings", {})
        holdings[symbol] = holdings.get(symbol, 0) + amount_crypto

        # Update in MongoDB
        self.db.portfolios.update_one(
            {"_id": self.portfolio_id},
            {"$set": {"balance_eur": new_balance, "holdings": holdings}}
        )

        # Record transaction
        transaction = {
            'timestamp': datetime.now(),
            'type': 'MANUAL_BUY',
            'symbol': symbol,
            'price_eur': price,
            'amount_eur': amount_eur,
            'amount_crypto': amount_crypto,
            'fee_eur': fee,
            'balance_after': new_balance,
            'portfolio_id': self.portfolio_id
        }
        self.db.transactions.insert_one(transaction)

        print(f"Successfully bought {amount_crypto} {symbol} for €{amount_eur}")
        print(f"New balance: €{new_balance}")
        return True

    def manual_sell(self, symbol, amount_crypto=None, price=None, fee_rate=FEE_RATE):
        """Manually record a sell transaction"""
        portfolio = self.get_portfolio()
        holdings = portfolio.get("holdings", {})

        if price is None:
            print("Error: You must specify the price")
            return False

        # Validate holdings
        if symbol not in holdings or holdings[symbol] <= 0:
            print(f"Error: No holdings for {symbol}")
            return False

        # If amount is None, sell all
        if amount_crypto is None or amount_crypto >= holdings[symbol]:
            amount_crypto = holdings[symbol]

        amount_eur = amount_crypto * price
        fee = amount_eur * fee_rate

        # Update balance and holdings
        new_balance = portfolio["balance_eur"] + (amount_eur - fee)
        holdings[symbol] -= amount_crypto

        # Update in MongoDB
        self.db.portfolios.update_one(
            {"_id": self.portfolio_id},
            {"$set": {"balance_eur": new_balance, "holdings": holdings}}
        )

        # Record transaction
        transaction = {
            'timestamp': datetime.now(),
            'type': 'MANUAL_SELL',
            'symbol': symbol,
            'price_eur': price,
            'amount_eur': amount_eur,
            'amount_crypto': amount_crypto,
            'fee_eur': fee,
            'balance_after': new_balance,
            'portfolio_id': self.portfolio_id
        }
        self.db.transactions.insert_one(transaction)

        print(f"Successfully sold {amount_crypto} {symbol} for €{amount_eur}")
        print(f"New balance: €{new_balance}")
        return True

    def transfer_crypto(self, symbol, amount_crypto):
        """Simulate transferring crypto to the account (price 0)"""
        portfolio = self.get_portfolio()
        holdings = portfolio.get("holdings", {})

        # Update holdings
        holdings[symbol] = holdings.get(symbol, 0) + amount_crypto

        # Update in MongoDB
        self.db.portfolios.update_one(
            {"_id": self.portfolio_id},
            {"$set": {"holdings": holdings}}
        )

        # Record transaction
        transaction = {
            'timestamp': datetime.now(),
            'type': 'CRYPTO_TRANSFER',
            'symbol': symbol,
            'amount_crypto': amount_crypto,
            'price_eur': 0,  # Zero price for transfers
            'portfolio_id': self.portfolio_id
        }
        self.db.transactions.insert_one(transaction)

        print(f"Successfully transferred {amount_crypto} {symbol} to your account")
        return True

    def display_portfolio(self):
        """Display the current portfolio status"""
        portfolio = self.get_portfolio()

        print("\n=== PORTFOLIO SUMMARY ===")
        print(f"Cash balance: €{portfolio['balance_eur']:.2f}")
        print("\nHoldings:")

        if not portfolio.get("holdings"):
            print("  No crypto holdings")
        else:
            for symbol, amount in portfolio.get("holdings", {}).items():
                if amount > 0:
                    print(f"  {symbol}: {amount}")

        print("\nRecent Transactions:")
        transactions = list(self.db.transactions.find(
            {"portfolio_id": self.portfolio_id}
        ).sort("timestamp", -1).limit(5))

        if not transactions:
            print("  No transactions yet")
        else:
            for tx in transactions:
                tx_type = tx["type"]
                timestamp = tx["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

                if tx_type == "DEPOSIT":
                    print(f"  {timestamp} - DEPOSIT: €{tx['amount_eur']}")
                elif tx_type == "WITHDRAWAL":
                    print(f"  {timestamp} - WITHDRAWAL: €{tx['amount_eur']}")
                elif tx_type in ["MANUAL_BUY", "BUY"]:
                    print(f"  {timestamp} - BUY: {tx['amount_crypto']} {tx['symbol']} at €{tx['price_eur']}")
                elif tx_type in ["MANUAL_SELL", "SELL"]:
                    print(f"  {timestamp} - SELL: {tx['amount_crypto']} {tx['symbol']} at €{tx['price_eur']}")
                elif tx_type == "CRYPTO_TRANSFER":
                    print(f"  {timestamp} - TRANSFER IN: {tx['amount_crypto']} {tx['symbol']}")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Portfolio Management Utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Display portfolio
    display_parser = subparsers.add_parser("display", help="Display portfolio summary")

    # Deposit funds
    deposit_parser = subparsers.add_parser("deposit", help="Deposit funds")
    deposit_parser.add_argument("amount", type=float, help="Amount in EUR to deposit")

    # Withdraw funds
    withdraw_parser = subparsers.add_parser("withdraw", help="Withdraw funds")
    withdraw_parser.add_argument("amount", type=float, help="Amount in EUR to withdraw")

    # Manual buy
    buy_parser = subparsers.add_parser("buy", help="Manually record a buy transaction")
    buy_parser.add_argument("symbol", type=str, help="Symbol to buy (e.g., BTC)")
    buy_parser.add_argument("--amount-eur", type=float, help="Amount in EUR to spend")
    buy_parser.add_argument("--amount-crypto", type=float, help="Amount of crypto to buy")
    buy_parser.add_argument("--price", type=float, required=True, help="Price per unit in EUR")

    # Manual sell
    sell_parser = subparsers.add_parser("sell", help="Manually record a sell transaction")
    sell_parser.add_argument("symbol", type=str, help="Symbol to sell (e.g., BTC)")
    sell_parser.add_argument("--amount-crypto", type=float, help="Amount of crypto to sell (all if not specified)")
    sell_parser.add_argument("--price", type=float, required=True, help="Price per unit in EUR")

    # Crypto transfer
    transfer_parser = subparsers.add_parser("transfer", help="Simulate transferring crypto to the account")
    transfer_parser.add_argument("symbol", type=str, help="Symbol to transfer (e.g., BTC)")
    transfer_parser.add_argument("amount", type=float, help="Amount of crypto to transfer")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    manager = PortfolioManager()

    if args.command == "display":
        manager.display_portfolio()
    elif args.command == "deposit":
        manager.deposit_funds(args.amount)
    elif args.command == "withdraw":
        manager.withdraw_funds(args.amount)
    elif args.command == "buy":
        manager.manual_buy(
            args.symbol,
            amount_eur=args.amount_eur,
            amount_crypto=args.amount_crypto,
            price=args.price
        )
    elif args.command == "sell":
        manager.manual_sell(
            args.symbol,
            amount_crypto=args.amount_crypto,
            price=args.price
        )
    elif args.command == "transfer":
        manager.transfer_crypto(args.symbol, args.amount)
    else:
        print("Please specify a command. Use --help for more information.")

# View your portfolio
# python portfolio_manager.py display

# Add €1000 to your account
# python portfolio_manager.py deposit 1000

# Manually buy BTC
# python portfolio_manager.py buy BTC --amount-eur 500 --price 25000

# Sell crypto
# python portfolio_manager.py sell BTC --amount-crypto 0.01 --price 26000

# Transfer crypto to your account (for free)
# python portfolio_manager.py transfer BTC 0.5

# Withdraw funds
# python portfolio_manager.py withdraw 200
