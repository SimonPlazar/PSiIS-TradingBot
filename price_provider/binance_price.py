from binance.client import Client

client = Client()

def get_best_prices(symbol):
    depth = client.get_order_book(symbol=symbol + 'EUR', limit=5)
    best_bid = float(depth["bids"][0][0])
    best_ask = float(depth["asks"][0][0])
    return best_bid, best_ask
