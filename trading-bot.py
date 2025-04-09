from kafka import KafkaConsumer
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
from bson import ObjectId
from binance.client import Client

FEE_RATE = 0.001

class Portfolio:
    def __init__(self, initial_balance_eur=10000.0, db_uri="mongodb://localhost:27017/"):
        self.client = Client()  # Binance client for price data

        # MongoDB setup
        self.mongo_client = MongoClient(db_uri)
        self.db = self.mongo_client.trading_bot

        # Check if portfolio exists, otherwise create it
        portfolio = self.db.portfolios.find_one({"active": True})
        if not portfolio:
            portfolio_id = self.db.portfolios.insert_one({
                "initial_balance_eur": initial_balance_eur,
                "balance_eur": initial_balance_eur,
                "holdings": {},
                "active": True,
                "created_at": datetime.now()
            }).inserted_id
            self.portfolio_id = portfolio_id
        else:
            self.portfolio_id = portfolio["_id"]

    def get_price(self, symbol):
        """Fetches the best bid/ask price (accounts for slippage)."""
        depth = self.client.get_order_book(symbol=symbol, limit=5)
        best_bid = float(depth["bids"][0][0])
        best_ask = float(depth["asks"][0][0])
        return best_bid, best_ask

    def get_portfolio(self):
        return self.db.portfolios.find_one({"_id": self.portfolio_id})

    def get_current_value_eur(self):
        portfolio = self.get_portfolio()
        total_value = portfolio["balance_eur"]

        for symbol, amount in portfolio["holdings"].items():
            if amount > 0:
                # Get current BTC price in EUR
                current_price = float(self.client.get_symbol_ticker(symbol=symbol + "EUR")['price'])
                total_value += amount * current_price
        return total_value

    def get_pnl(self):
        portfolio = self.get_portfolio()
        return self.get_current_value_eur() - portfolio["initial_balance_eur"]

    def get_asset_distribution(self):
        """Calculate what percentage of portfolio is in each asset"""
        portfolio = self.get_portfolio()
        total_value = self.get_current_value_eur()
        distribution = {"EUR": (portfolio["balance_eur"] / total_value) * 100}

        for symbol, amount in portfolio["holdings"].items():
            if amount > 0:
                current_price = float(self.client.get_symbol_ticker(symbol=symbol + "EUR")['price'])
                asset_value = amount * current_price
                distribution[symbol] = (asset_value / total_value) * 100

        return distribution

    def simulate_buy(self, symbol, amount_eur, fee_rate=FEE_RATE):
        portfolio = self.get_portfolio()
        balance_eur = portfolio["balance_eur"]

        # Validation: check if we have enough balance
        if balance_eur < amount_eur:
            return False, "Insufficient balance"

        best_bid, best_ask = self.get_price(symbol + "EUR")
        amount_crypto = amount_eur / best_ask
        fee = amount_eur * fee_rate

        # Update balance and holdings
        new_balance = balance_eur - (amount_eur + fee)
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
            'type': 'BUY',
            'symbol': symbol,
            'price_eur': best_ask,
            'amount_eur': amount_eur,
            'amount_crypto': amount_crypto,
            'fee_eur': fee,
            'portfolio_id': self.portfolio_id
        }
        self.db.transactions.insert_one(transaction)

        return True, transaction

    def simulate_sell(self, symbol, amount_crypto=None, fee_rate=FEE_RATE):
        portfolio = self.get_portfolio()
        holdings = portfolio.get("holdings", {})

        # Validation: check if we have the crypto
        if symbol not in holdings or holdings[symbol] <= 0:
            return False, "No holdings for this symbol"

        best_bid, best_ask = self.get_price(symbol + "EUR")

        if amount_crypto is None or amount_crypto >= holdings[symbol]:
            amount_crypto = holdings[symbol]  # Sell all

        amount_eur = amount_crypto * best_bid
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
            'type': 'SELL',
            'symbol': symbol,
            'price_eur': best_bid,
            'amount_eur': amount_eur,
            'amount_crypto': amount_crypto,
            'fee_eur': fee,
            'portfolio_id': self.portfolio_id
        }
        self.db.transactions.insert_one(transaction)

        return True, transaction

    def add_funds(self, amount_eur):
        """Add more funds to the portfolio"""
        portfolio = self.get_portfolio()
        new_balance = portfolio["balance_eur"] + amount_eur

        self.db.portfolios.update_one(
            {"_id": self.portfolio_id},
            {"$set": {"balance_eur": new_balance}}
        )

        return True, {"new_balance": new_balance}

    def get_transaction_history(self):
        """Get all transactions for this portfolio"""
        return list(self.db.transactions.find({"portfolio_id": self.portfolio_id}).sort("timestamp", -1))


def start_trading_bot():
    portfolio = Portfolio(initial_balance_eur=10000.0)

    # Set up Kafka consumer
    consumer = KafkaConsumer(
        'trading_signals',
        bootstrap_servers=['localhost:9092'],
        auto_offset_reset='latest',
        value_deserializer=lambda x: pd.json.loads(x.decode('utf-8'))
    )

    print("Trading bot started, waiting for signals...")

    for message in consumer:
        signal = message.value
        print(f"Received signal: {signal}")

        action = signal.get('action')
        symbol = signal.get('symbol')
        amount = signal.get('amount', 100)  # Default €100 or specific amount

        if action == 'BUY':
            success, result = portfolio.simulate_buy(symbol, amount)
        elif action == 'SELL':
            success, result = portfolio.simulate_sell(symbol)

        current_value = portfolio.get_current_value_eur()
        pnl = portfolio.get_pnl()
        pnl_percentage = (pnl / portfolio.get_portfolio()["initial_balance_eur"]) * 100
        distribution = portfolio.get_asset_distribution()

        print(f"Portfolio value: €{current_value:.2f}")
        print(f"P&L: €{pnl:.2f} ({pnl_percentage:.2f}%)")
        print(f"Asset distribution: {distribution}")
        print("-" * 50)