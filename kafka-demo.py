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


if __name__ == "__main__":
    producer = create_producer()

    send_signal(producer, 'buy', symbol='BTCUSD', amount=100)

    time.sleep(2)

    send_signal(producer, 'sell', symbol='ETHUSD', amount=50)

    time.sleep(2)

    send_signal(producer, 'buy', symbol='XRPUSD', amount=200)

