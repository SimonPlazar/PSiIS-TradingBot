import os

import pymongo
from pymongo import MongoClient

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

URI = os.getenv("MONGODB_URL")

# Sample transaction
transaction = {
    "type": "buy",
    "asset": "BTC",
    "amount": 0.5,
    "price": 30000,
    "timestamp": "2025-04-10T12:34:56Z"
}


try:
    client = MongoClient(URI, server_api=pymongo.server_api.ServerApi(
        version="1", strict=True, deprecation_errors=True))

    client.admin.command("ping")
    print("MongoDB connection successful.")

    database = client["sample_mflix"]
    collection = database["comments"]

    # get all documents in the collection
    documents = collection.find()
    for doc in documents:
        print(doc)

    client.close()

except Exception as e:
    print("MongoDB connection failed:", e)



