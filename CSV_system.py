import pandas as pd
import json
from kafka import KafkaProducer
from dotenv import load_dotenv
import os

load_dotenv()
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Read from CSV and send to Kafka
df = pd.read_csv("input_signals.csv")

for _, row in df.iterrows():
    signal = row.to_dict()
    producer.send('trading_signals', signal)

print("Signals sent from CSV.")

# Save received signals to a CSV
signals = []
def save_signal(signal):
    signals.append(signal)
    pd.DataFrame(signals).to_csv("received_signals.csv", index=False)
