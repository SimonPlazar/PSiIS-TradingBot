from kafka import KafkaConsumer
from signal_processor import process_signal
import json
from dotenv import load_dotenv
import os

load_dotenv()
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

consumer = KafkaConsumer(
    'trading_signals',
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset='latest',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

print("📥 Kafka consumer started, waiting for signals...")

for msg in consumer:
    signal = msg.value
    try:
        print(f"📨 Received signal: {signal}")
        process_signal(signal)
        print("✅ Signal processed successfully.\n")
    except Exception as e:
        print(f"❌ Failed to process signal: {e}\n")
