import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# Get MongoDB connection string from environment variables or use default
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("MONGODB_DB_NAME", "assistant_db")

# Collections
CONVERSATIONS_COLLECTION = "conversations"
MESSAGES_COLLECTION = "messages"


class MongoDBClient:
    def __init__(self):
        self.client = None
        self.db = None
        self._connect()

    def _connect(self):
        """Connect to MongoDB using the URI from environment variables."""
        try:
            mongo_uri = os.getenv("MONGODB_URI", "mongodb://assistant_mongodb:27017/assistant_db")
            self.client = MongoClient(mongo_uri)
            self.db = self.client.get_database()
            print(f"Connected to MongoDB: {mongo_uri}")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            self.client = None
            self.db = None

    def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            if self.client is None:
                return False

            # Ping the database to check connection
            self.client.admin.command('ping')
            return True
        except Exception as e:
            print(f"MongoDB health check failed: {e}")
            return False

    # === Conversation methods ===

    def create_conversation(self, conversation_id: str, title: str) -> Dict[str, Any]:
        """Create a new conversation with the provided ID"""
        if self.client is None:
            print("[MONGODB] Database not connected, skipping create_conversation")
            return None

        # Check if conversation already exists to avoid duplicates
        existing = self.get_conversation(conversation_id)
        if existing:
            print(f"[MONGODB] Conversation with ID {conversation_id} already exists")
            return existing

        now = datetime.now().isoformat()
        conversation = {
            "conversation_id": conversation_id,
            "title": title,
            "created_at": now,
            "updated_at": now
        }

        try:
            self.db[CONVERSATIONS_COLLECTION].insert_one(conversation)
            print(f"[MONGODB] Created conversation: {conversation_id}")
            return conversation
        except Exception as e:
            print(f"[MONGODB] Error creating conversation: {str(e)}")
            return None

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID"""
        if self.client is None:
            return None

        return self.db[CONVERSATIONS_COLLECTION].find_one(
            {"conversation_id": conversation_id},
            {"_id": 0}  # Exclude MongoDB's _id field
        )

    def list_conversations(self) -> List[Dict[str, Any]]:
        """List all conversations"""
        if self.client is None:
            return []

        return list(self.db[CONVERSATIONS_COLLECTION].find(
            {},
            {"_id": 0}
        ).sort("updated_at", -1))  # Sort by updated_at descending

    def update_conversation(self, conversation_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a conversation"""
        if self.client is None:
            return None

        # Always update the updated_at timestamp
        updates["updated_at"] = datetime.now().isoformat()

        result = self.db[CONVERSATIONS_COLLECTION].update_one(
            {"conversation_id": conversation_id},
            {"$set": updates}
        )

        if result.matched_count == 0:
            return None

        return self.get_conversation(conversation_id)

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and its messages"""
        if self.client is None:
            return False

        # Delete the conversation
        result = self.db[CONVERSATIONS_COLLECTION].delete_one({"conversation_id": conversation_id})

        # Delete all messages for this conversation
        self.db[MESSAGES_COLLECTION].delete_many({"conversation_id": conversation_id})

        return result.deleted_count > 0

    # === Message methods ===

    def save_message(self, conversation_id: str, message: Dict[str, Any]) -> str:
        """Save a message to a conversation"""
        if self.client is None:
            return None

        # Add conversation_id and timestamp
        message_doc = {
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            **message  # Include all fields from the message
        }

        result = self.db[MESSAGES_COLLECTION].insert_one(message_doc)

        # Update the conversation's updated_at timestamp
        self.update_conversation(conversation_id, {"updated_at": message_doc["timestamp"]})

        # Return the message ID
        return str(result.inserted_id)

    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a conversation"""
        if self.client is None:
            return []

        return list(self.db[MESSAGES_COLLECTION].find(
            {"conversation_id": conversation_id},
            {"_id": 0}  # Exclude MongoDB's _id field
        ).sort("timestamp", 1))  # Sort by timestamp ascending


# Initialize MongoDB client
mongo_db = MongoDBClient()
