from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from .models import Conversation, ConversationCreate, ConversationUpdate

router = APIRouter()

# In-memory conversation storage
conversations = {}

# Utility for validating conversation existence
async def get_conversation(conversation_id: str):
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversations[conversation_id]

@router.post("/conversations", response_model=Conversation)
async def create_conversation(conversation_data: ConversationCreate):
    """Create a new conversation thread using the provided ID"""
    # Check if conversation with provided ID already exists
    if conversation_data.conversation_id in conversations:
        raise HTTPException(
            status_code=400, 
            detail=f"Conversation with ID {conversation_data.conversation_id} already exists"
        )
    
    now = datetime.now().isoformat()
    conversation = Conversation(
        conversation_id=conversation_data.conversation_id,
        title=conversation_data.title,
        created_at=now,
        updated_at=now
    )
    conversations[conversation_data.conversation_id] = conversation
    return conversation

@router.get("/conversations", response_model=List[Conversation])
async def list_conversations():
    """List all conversation threads"""
    return list(conversations.values())

@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation_by_id(conversation: Conversation = Depends(get_conversation)):
    """Get a specific conversation by ID"""
    return conversation

@router.put("/conversations/{conversation_id}", response_model=Conversation)
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

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation: Conversation = Depends(get_conversation)):
    """Delete a conversation"""
    del conversations[conversation.conversation_id]
    return {"status": "success", "message": f"Conversation {conversation.conversation_id} deleted"}
