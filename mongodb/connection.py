import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/farmaceutica_tp")
DB_NAME = MONGO_URI.rsplit("/", 1)[-1].split("?")[0] or "farmaceutica"


def get_client() -> MongoClient:
    return MongoClient(MONGO_URI)


def get_db():
    client = get_client()
    return client[DB_NAME]
