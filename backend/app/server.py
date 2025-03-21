from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends
from .langgraph.agent import assistant_ui_graph
from .add_langgraph_route import add_langgraph_route
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

app = FastAPI()
# cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# In-memory conversation storage
conversations = {}

# Add routes with the new URL structure
add_langgraph_route(app, assistant_ui_graph, "/api")

# Utility for validating conversation existence
async def get_conversation(conversation_id: str):
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversations[conversation_id]

@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(conversation_data: ConversationCreate):
    """Create a new conversation thread for memory persistence"""
    now = datetime.now().isoformat()
    conversation_id = str(uuid.uuid4())
    conversation = Conversation(
        conversation_id=conversation_id,
        title=conversation_data.title,
        created_at=now,
        updated_at=now
    )
    conversations[conversation_id] = conversation
    return conversation

@app.get("/api/conversations", response_model=List[Conversation])
async def list_conversations():
    """List all conversation threads"""
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
    if conversation_data.title is not None:
        conversation.title = conversation_data.title
    
    conversation.updated_at = datetime.now().isoformat()
    conversations[conversation.conversation_id] = conversation
    return conversation

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation: Conversation = Depends(get_conversation)):
    """Delete a conversation"""
    del conversations[conversation.conversation_id]
    return {"status": "success", "message": f"Conversation {conversation.conversation_id} deleted"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
