from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from .add_langgraph_route import add_langgraph_route
from .database.mongo_client import mongo_db
from .knowledge.routes import router as knowledge_router
from .langgraph.agent import assistant_ui_graph
from .models import (
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    StatusResponse,
    HealthCheckResponse
)

print("\n[SERVER] Initializing FastAPI application")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("[SERVER] Added CORS middleware")

if mongo_db.health_check():
    print("[SERVER] MongoDB connection successful")
else:
    print("[SERVER] WARNING: MongoDB connection failed, falling back to in-memory storage")

conversations = {}

print("[SERVER] Adding LangGraph routes")
add_langgraph_route(app, assistant_ui_graph, "/api")

print("[SERVER] Adding knowledge management routes")
app.include_router(knowledge_router, prefix="/api")


async def get_conversation(conversation_id: str):
    if mongo_db.health_check():
        conversation = mongo_db.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return Conversation(**conversation)

    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversations[conversation_id]


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(conversation_data: ConversationCreate):
    """Create a new conversation thread using the client-provided ID"""
    print(f"\n[SERVER] Creating new conversation with ID: {conversation_data.conversation_id}")

    if mongo_db.health_check():
        existing = mongo_db.get_conversation(conversation_data.conversation_id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Conversation with ID {conversation_data.conversation_id} already exists"
            )

        conversation = mongo_db.create_conversation(
            conversation_id=conversation_data.conversation_id,
            title=conversation_data.title
        )
        if conversation:
            return Conversation(**conversation)

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

    print(f"[SERVER] Created conversation with ID: {conversation_data.conversation_id}")
    return conversation


@app.get("/api/conversations", response_model=List[Conversation])
async def list_conversations():
    """List all conversation threads"""
    if mongo_db.health_check():
        mongo_conversations = mongo_db.list_conversations()
        return [Conversation(**conv) for conv in mongo_conversations]

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

    if mongo_db.health_check():
        updated_conversation = mongo_db.update_conversation(
            conversation_id=conversation.conversation_id,
            updates={"title": conversation_data.title}
        )
        if updated_conversation:
            return Conversation(**updated_conversation)

    conversation.title = conversation_data.title
    conversation.updated_at = datetime.now().isoformat()
    conversations[conversation.conversation_id] = conversation

    return conversation


@app.delete("/api/conversations/{conversation_id}", response_model=StatusResponse)
async def delete_conversation(conversation: Conversation = Depends(get_conversation)):
    """Delete a conversation"""
    if mongo_db.health_check():
        success = mongo_db.delete_conversation(conversation.conversation_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete conversation")
    else:
        del conversations[conversation.conversation_id]

    return StatusResponse(
        status="success",
        message=f"Conversation {conversation.conversation_id} deleted"
    )


@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check():
    """API health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        mongodb=mongo_db.health_check()
    )


if __name__ == "__main__":
    import uvicorn

    print("[SERVER] Starting Uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
