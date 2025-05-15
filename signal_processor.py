from datetime import datetime
from pymongo.errors import PyMongoError
from price_provider.binance_price import get_best_prices
from portfolio_manager_cli import PortfolioManager

FEE_RATE = 0.001

manager = PortfolioManager()

def process_signal(signal: dict):
    from_currency = signal["from_symbol"]
    to_currency = signal["to_symbol"]
    action = signal["action"]
    amount = float(signal["amount"])

    with manager.client.start_session() as session:
        try:
            with session.start_transaction():
                from_asset = manager.get_currency(from_currency, session=session)
                to_asset = manager.get_currency(to_currency, session=session, create_if_missing=True)

                best_bid, best_ask = get_best_prices(to_currency)
                rate = best_ask if action == "BUY" else best_bid

                if action == "BUY":
                    if from_asset["balance"] < amount:
                        raise ValueError("Insufficient balance to buy")

                    to_amount = amount / rate
                    fee = amount * FEE_RATE

                    manager.update_balance(from_currency, -(amount + fee), session=session)
                    manager.update_balance(to_currency, to_amount, session=session)

                    manager.record_transaction({
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
                        raise ValueError("No holdings of target asset to sell")

                    to_amount = to_asset["balance"]
                    from_amount = to_amount * rate
                    fee = from_amount * FEE_RATE

                    manager.set_balance(to_currency, 0, session=session)
                    manager.update_balance(from_currency, from_amount - fee, session=session)

                    manager.record_transaction({
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
            print(f"❌ MongoDB transaction failed: {e}")
        except Exception as e:
            print(f"❌ Signal processing error: {e}")
