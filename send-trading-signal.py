from kafka import KafkaProducer
import json
import time
import argparse
from datetime import datetime


def create_producer():
    """Create and return a Kafka producer instance"""
    return KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )


def send_signal(producer, action, symbol, amount=100):
    """Send a trading signal to Kafka"""
    signal = {
        'action': action,
        'symbol': symbol,
        'amount': amount,
        'timestamp': datetime.now().isoformat()
    }

    producer.send('trading_signals', signal)
    producer.flush()
    print(f"Sent signal: {signal}")


def demo_sequence():
    """Run a demo sequence of trading signals"""
    producer = create_producer()

    print("Starting trading signal demo sequence...")

    # Buy some BTC
    send_signal(producer, 'BUY', 'BTC', 200)
    time.sleep(2)

    # Buy some ETH
    send_signal(producer, 'BUY', 'ETH', 150)
    time.sleep(2)

    # Buy some XRP
    send_signal(producer, 'BUY', 'XRP', 100)
    time.sleep(2)

    # Sell BTC
    send_signal(producer, 'SELL', 'BTC')
    time.sleep(2)

    # Buy more ETH
    send_signal(producer, 'BUY', 'ETH', 300)
    time.sleep(2)

    # Sell XRP
    send_signal(producer, 'SELL', 'XRP')

    print("Demo sequence completed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Send trading signals to Kafka')

    parser.add_argument('--mode', choices=['demo', 'single'], default='demo',
                        help='Run demo sequence or send a single signal')

    parser.add_argument('--action', choices=['BUY', 'SELL'],
                        help='Trading action for single mode')

    parser.add_argument('--symbol', type=str,
                        help='Trading symbol (e.g., BTC, ETH) for single mode')

    parser.add_argument('--amount', type=float, default=100,
                        help='Amount in EUR for BUY orders (default: 100)')

    args = parser.parse_args()

    if args.mode == 'demo':
        demo_sequence()
    else:
        if not args.action or not args.symbol:
            print("Error: --action and --symbol are required for single mode")
            parser.print_help()
        else:
            producer = create_producer()
            send_signal(producer, args.action, args.symbol, args.amount)