from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends
from .langgraph.agent import assistant_ui_graph
from .add_langgraph_route import add_langgraph_route
from .knowledge.routes import router as knowledge_router
from .database.mongo_client import mongo_db
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

# Add logging to server startup
print("\n[SERVER] Initializing FastAPI application")

app = FastAPI()
# cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("[SERVER] Added CORS middleware")

# Check MongoDB connection
if mongo_db.health_check():
    print("[SERVER] MongoDB connection successful")
else:
    print("[SERVER] WARNING: MongoDB connection failed, falling back to in-memory storage")

# Models for conversation management
class Conversation(BaseModel):
    conversation_id: str
    title: Optional[str] = "New Conversation"
    created_at: str
    updated_at: str

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"

class ConversationUpdate(BaseModel):
    title: Optional[str] = None

# In-memory conversation storage (fallback if MongoDB isn't available)
conversations = {}

# Add routes with the new URL structure
print("[SERVER] Adding LangGraph routes")
add_langgraph_route(app, assistant_ui_graph, "/api")

# Include knowledge management routes
print("[SERVER] Adding knowledge management routes")
app.include_router(knowledge_router, prefix="/api")

# Utility for validating conversation existence
async def get_conversation(conversation_id: str):
    # Try to get from MongoDB first
    if mongo_db.health_check():
        conversation = mongo_db.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return Conversation(**conversation)
    
    # Fall back to in-memory if MongoDB is unavailable
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversations[conversation_id]

@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(conversation_data: ConversationCreate):
    """Create a new conversation thread for memory persistence"""
    print(f"\n[SERVER] Creating new conversation: {conversation_data.title}")
    
    conversation_id = str(uuid.uuid4())
    
    # Use MongoDB if available
    if mongo_db.health_check():
        conversation = mongo_db.create_conversation(
            conversation_id=conversation_id,
            title=conversation_data.title
        )
        if conversation:
            return Conversation(**conversation)
    
    # Fall back to in-memory storage
    now = datetime.now().isoformat()
    conversation = Conversation(
        conversation_id=conversation_id,
        title=conversation_data.title,
        created_at=now,
        updated_at=now
    )
    conversations[conversation_id] = conversation
    
    print(f"[SERVER] Created conversation with ID: {conversation_id}")
    return conversation

@app.get("/api/conversations", response_model=List[Conversation])
async def list_conversations():
    """List all conversation threads"""
    # Use MongoDB if available
    if mongo_db.health_check():
        mongo_conversations = mongo_db.list_conversations()
        return [Conversation(**conv) for conv in mongo_conversations]
    
    # Fall back to in-memory storage
    return list(conversations.values())

@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation_by_id(conversation: Conversation = Depends(get_conversation)):
    """Get a specific conversation by ID"""
    return conversation

@app.put("/api/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_data: ConversationUpdate, 
    conversation: Conversation = Depends(get_conversation)
):
    """Update a conversation title"""
    if conversation_data.title is None:
        return conversation
    
    # Use MongoDB if available
    if mongo_db.health_check():
        updated_conversation = mongo_db.update_conversation(
            conversation_id=conversation.conversation_id,
            updates={"title": conversation_data.title}
        )
        if updated_conversation:
            return Conversation(**updated_conversation)
    
    # Fall back to in-memory storage
    conversation.title = conversation_data.title
    conversation.updated_at = datetime.now().isoformat()
    conversations[conversation.conversation_id] = conversation
    
    return conversation

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation: Conversation = Depends(get_conversation)):
    """Delete a conversation"""
    # Use MongoDB if available
    if mongo_db.health_check():
        success = mongo_db.delete_conversation(conversation.conversation_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete conversation")
    else:
        # Fall back to in-memory storage
        del conversations[conversation.conversation_id]
    
    return {"status": "success", "message": f"Conversation {conversation.conversation_id} deleted"}

@app.get("/api/health")
async def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "mongodb": mongo_db.health_check()
    }

if __name__ == "__main__":
    import uvicorn

    print("[SERVER] Starting Uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
