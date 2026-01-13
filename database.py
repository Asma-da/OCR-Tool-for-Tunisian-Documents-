from pymongo import MongoClient
from config import Config

# Connect to MongoDB
client = MongoClient(Config.MONGO_URI)

# Explicitly use the "OCR" database
db = client[Config.DATABASE_NAME]


def get_collection(name: str):
    """
    Returns a collection from the OCR database.
    """
    return db[name]


# Helper functions for specific collections
def get_user_collection():
    return get_collection("users")


def get_ocr_collection():
    return get_collection("uploads")