"""
Utility script to initialize MongoDB collections and indexes.
Run this script once before starting your application to set up the database structure.
"""

import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("MONGODB_DB_NAME", "assistant_db")

CONVERSATIONS_COLLECTION = "conversations"
MESSAGES_COLLECTION = "messages"


def initialize_database():
    """Initialize MongoDB database with required collections and indexes"""
    try:
        print(f"Connecting to MongoDB at {MONGODB_URI}...")
        client = MongoClient(MONGODB_URI)
        db = client[DB_NAME]

        if CONVERSATIONS_COLLECTION not in db.list_collection_names():
            db.create_collection(CONVERSATIONS_COLLECTION)
            print(f"Created collection: {CONVERSATIONS_COLLECTION}")

        if MESSAGES_COLLECTION not in db.list_collection_names():
            db.create_collection(MESSAGES_COLLECTION)
            print(f"Created collection: {MESSAGES_COLLECTION}")

        db[MESSAGES_COLLECTION].create_index("conversation_id")
        print(f"Created index on conversation_id for {MESSAGES_COLLECTION} collection")

        db[CONVERSATIONS_COLLECTION].create_index("conversation_id")
        print(f"Created index on conversation_id for {CONVERSATIONS_COLLECTION} collection")

        client.admin.command('ping')
        print(f"Successfully connected to MongoDB at {MONGODB_URI}")
        print(f"Database {DB_NAME} initialized with required collections and indexes")

        return True
    except Exception as e:
        print(f"Error initializing MongoDB: {str(e)}")
        return False


if __name__ == "__main__":
    print("Initializing MongoDB database...")
    success = initialize_database()

    if success:
        print("Database initialization completed successfully.")
    else:
        print("Database initialization failed. Check your MongoDB connection.")
