from pymongo import MongoClient
from pymongo.errors import PyMongoError
from datetime import datetime
from price_provider.binance_price import get_best_prices
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_USER = os.getenv("MONGO_INITDB_ROOT_USERNAME")
MONGO_PASS = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
MONGO_DB = os.getenv("MONGO_INITDB_DATABASE")
MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASS}@localhost:27017/?authSource={MONGO_DB}"

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

FEE_RATE = 0.001

def process_signal(signal):
    from_currency = signal["from_symbol"]
    to_currency = signal["to_symbol"]
    action = signal["action"]
    amount = float(signal["amount"])

    with client.start_session() as session:
        try:
            with session.start_transaction():
                from_asset = db.currencies.find_one({"symbol": from_currency}, session=session)
                to_asset = db.currencies.find_one({"symbol": to_currency}, session=session) or {"symbol": to_currency, "balance": 0}
                best_bid, best_ask = get_best_prices(to_currency)
                rate = best_ask if action == "BUY" else best_bid

                if action == "BUY":
                    if from_asset["balance"] < amount:
                        raise Exception("Insufficient balance")
                    to_amount = amount / rate
                    fee = amount * FEE_RATE

                    db.currencies.update_one({"symbol": from_currency}, {"$inc": {"balance": -(amount + fee)}}, session=session)
                    db.currencies.update_one({"symbol": to_currency}, {"$inc": {"balance": to_amount}}, upsert=True, session=session)

                    db.transactions.insert_one({
                        "from_currency": from_currency,
                        "from_amount": amount,
                        "to_currency": to_currency,
                        "to_amount": to_amount,
                        "rate": rate,
                        "fee": fee,
                        "timestamp": datetime.utcnow(),
                        "source": "recommender"
                    }, session=session)

                elif action == "SELL":
                    if to_asset["balance"] <= 0:
                        raise Exception("No holdings of target asset")

                    to_amount = to_asset["balance"]
                    from_amount = to_amount * rate
                    fee = from_amount * FEE_RATE

                    db.currencies.update_one({"symbol": to_currency}, {"$set": {"balance": 0}}, session=session)
                    db.currencies.update_one({"symbol": from_currency}, {"$inc": {"balance": from_amount - fee}}, session=session)

                    db.transactions.insert_one({
                        "from_currency": to_currency,
                        "from_amount": to_amount,
                        "to_currency": from_currency,
                        "to_amount": from_amount,
                        "rate": rate,
                        "fee": fee,
                        "timestamp": datetime.utcnow(),
                        "source": "recommender"
                    }, session=session)

        except PyMongoError as e:
            print(f"Transaction failed: {e}")
