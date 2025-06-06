from binance.client import Client


client = Client()  # No API key needed for public endpoints

price = client.get_symbol_ticker(symbol="BTCUSDT")
print(price)

depth = client.get_order_book(symbol="BTCUSDT", limit=5)
print(depth)

# Get trading info for BTCUSDT
symbol_info = client.get_symbol_info("BTCUSDT")
print(symbol_info)

FEE_RATE = 0.001  # 0.1% fee


def get_price(symbol):
    """Fetches the best bid/ask price (accounts for slippage)."""
    depth = client.get_order_book(symbol=symbol, limit=5)
    best_bid = float(depth["bids"][0][0])
    best_ask = float(depth["asks"][0][0])
    return best_bid, best_ask


from kafka import KafkaConsumer
import pandas as pd


if "main" in __name__:
    # Set up Kafka consumer
    consumer = KafkaConsumer(
        'trading_signals',
        bootstrap_servers=['localhost:9092'],
        auto_offset_reset='latest',
        value_deserializer=lambda x: pd.json.loads(x.decode('utf-8'))
    )

    for message in consumer:
        signal = message.value
        print(f"Received signal: {signal}")

