"""
Utility script to initialize MongoDB collections and indexes.
Run this script once before starting your application to set up the database structure.
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get MongoDB connection string from environment variables or use default
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("MONGODB_DB_NAME", "assistant_db")

# Collections
CONVERSATIONS_COLLECTION = "conversations"
MESSAGES_COLLECTION = "messages"

def initialize_database():
    """Initialize MongoDB database with required collections and indexes"""
    try:
        client = MongoClient(MONGODB_URI)
        db = client[DB_NAME]
        
        # Create conversations collection if it doesn't exist
        if CONVERSATIONS_COLLECTION not in db.list_collection_names():
            db.create_collection(CONVERSATIONS_COLLECTION)
            print(f"Created collection: {CONVERSATIONS_COLLECTION}")
        
        # Create messages collection if it doesn't exist
        if MESSAGES_COLLECTION not in db.list_collection_names():
            db.create_collection(MESSAGES_COLLECTION)
            print(f"Created collection: {MESSAGES_COLLECTION}")
        
        # Create indexes for better query performance
        db[MESSAGES_COLLECTION].create_index("conversation_id")
        print(f"Created index on conversation_id for {MESSAGES_COLLECTION} collection")
        
        # Create index but remove the unique constraint, allowing clients to set their own IDs
        # and handle potential duplicates at the application level
        db[CONVERSATIONS_COLLECTION].create_index("conversation_id")
        print(f"Created index on conversation_id for {CONVERSATIONS_COLLECTION} collection")
        
        # Check connection by performing a simple command
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
