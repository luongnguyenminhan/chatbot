from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
import json
import asyncio
from assistant_stream import create_run, RunController
from assistant_stream.serialization import DataStreamResponse
from langchain_core.messages import (
    HumanMessage,
    AIMessageChunk,
    AIMessage,
    ToolMessage,
    SystemMessage,
    BaseMessage,
)
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Literal, Union, Optional, Any
import uuid
from .database.mongo_client import mongo_db


class LanguageModelTextPart(BaseModel):
    type: Literal["text"]
    text: str
    providerMetadata: Optional[Any] = None


class LanguageModelImagePart(BaseModel):
    type: Literal["image"]
    image: str  # Will handle URL or base64 string
    mimeType: Optional[str] = None
    providerMetadata: Optional[Any] = None


class LanguageModelFilePart(BaseModel):
    type: Literal["file"]
    data: str  # URL or base64 string
    mimeType: str
    providerMetadata: Optional[Any] = None


class LanguageModelToolCallPart(BaseModel):
    type: Literal["tool-call"]
    toolCallId: str
    toolName: str
    args: Any
    providerMetadata: Optional[Any] = None


class LanguageModelToolResultContentPart(BaseModel):
    type: Literal["text", "image"]
    text: Optional[str] = None
    data: Optional[str] = None
    mimeType: Optional[str] = None


class LanguageModelToolResultPart(BaseModel):
    type: Literal["tool-result"]
    toolCallId: str
    toolName: str
    result: Any
    isError: Optional[bool] = None
    content: Optional[List[LanguageModelToolResultContentPart]] = None
    providerMetadata: Optional[Any] = None


class LanguageModelSystemMessage(BaseModel):
    role: Literal["system"]
    content: str


class LanguageModelUserMessage(BaseModel):
    role: Literal["user"]
    content: List[
        Union[LanguageModelTextPart, LanguageModelImagePart, LanguageModelFilePart]
    ]


class LanguageModelAssistantMessage(BaseModel):
    role: Literal["assistant"]
    content: List[Union[LanguageModelTextPart, LanguageModelToolCallPart]]


class LanguageModelToolMessage(BaseModel):
    role: Literal["tool"]
    content: List[LanguageModelToolResultPart]


LanguageModelV1Message = Union[
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
    LanguageModelAssistantMessage,
    LanguageModelToolMessage,
]


def convert_to_langchain_messages(
    messages: List[LanguageModelV1Message],
) -> List[BaseMessage]:
    result = []

    for msg in messages:
        if msg.role == "system":
            result.append(SystemMessage(content=msg.content))

        elif msg.role == "user":
            content = []
            for p in msg.content:
                if isinstance(p, LanguageModelTextPart):
                    content.append({"type": "text", "text": p.text})
                elif isinstance(p, LanguageModelImagePart):
                    content.append({"type": "image_url", "image_url": p.image})
            result.append(HumanMessage(content=content))

        elif msg.role == "assistant":
            # Handle both text and tool calls
            text_parts = [
                p for p in msg.content if isinstance(p, LanguageModelTextPart)
            ]
            text_content = " ".join(p.text for p in text_parts)
            tool_calls = [
                {
                    "id": p.toolCallId,
                    "name": p.toolName,
                    "args": p.args,
                }
                for p in msg.content
                if isinstance(p, LanguageModelToolCallPart)
            ]
            result.append(AIMessage(content=text_content, tool_calls=tool_calls))

        elif msg.role == "tool":
            for tool_result in msg.content:
                result.append(
                    ToolMessage(
                        content=str(tool_result.result),
                        tool_call_id=tool_result.toolCallId,
                    )
                )

    return result


def save_message_to_mongodb(conversation_id: str, role: str, content: str, tool_info: Optional[dict] = None):
    """Save a message to MongoDB if the connection is available"""
    if mongo_db.health_check():
        message_data = {
            "role": role,
            "content": content,
        }
        
        # Add tool information if provided
        if tool_info:
            message_data["tool_info"] = tool_info
            
        mongo_db.save_message(conversation_id, message_data)
        return True
    return False


class FrontendToolCall(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: dict[str, Any]


class ChatRequest(BaseModel):
    system: Optional[str] = ""
    tools: Optional[List[FrontendToolCall]] = []
    messages: List[LanguageModelV1Message]
    # No thread_id field since it comes from path parameter


def add_langgraph_route(app: FastAPI, graph, base_path: str):
    async def chat_completions(conversation_id: str, request: ChatRequest):
        
        inputs = convert_to_langchain_messages(request.messages)
        
        # Save user message to MongoDB
        for msg in request.messages:
            if msg.role == "user":
                # Extract text from user message
                text_content = ""
                for part in msg.content:
                    if isinstance(part, LanguageModelTextPart):
                        text_content += part.text
                
                if text_content:
                    save_message_to_mongodb(conversation_id, "user", text_content)
        
        # Use conversation_id from URL path for thread persistence
        thread_id = conversation_id

        # Custom streaming implementation
        async def stream_response():
            """Stream response with proper Unicode handling"""
            
            # Pass thread_id to the graph configuration
            config = {
                "configurable": {
                    "system": request.system,
                    "frontend_tools": request.tools,
                    "thread_id": thread_id
                }
            }
            
            message_count = 0
            full_response = ""  
            
            try:
                
                yield "data: {}\n\n"
                
                async for msg, metadata in graph.astream(
                    {"messages": inputs},
                    config,
                    stream_mode="messages",
                ):
                    message_count += 1
                    
                    if isinstance(msg, AIMessageChunk) or isinstance(msg, AIMessage):
                        if msg.content:
                           
                            

                            
                            # Send as JSON to preserve Unicode
                            json_data = json.dumps({"text": msg.content})
                            yield f"data: {json_data}\n\n"
                            
                            # Collect content for saving to MongoDB
                            full_response += msg.content
                    
                    elif isinstance(msg, ToolMessage):
                        json_data = json.dumps({"tool": msg.tool_call_id, "result": msg.content})
                        yield f"data: {json_data}\n\n"
                        
                        # Save tool messages to MongoDB
                        save_message_to_mongodb(
                            conversation_id, 
                            "tool", 
                            msg.content, 
                            {"tool_call_id": msg.tool_call_id}
                        )
                
                # Save the complete assistant response to MongoDB
                if full_response:
                    # Clean up any hidden conversation ID markers
                    clean_response = full_response.replace(f"\n<!--conversation_id:{thread_id}-->", "")
                    save_message_to_mongodb(conversation_id, "assistant", clean_response)
                
                # Add conversation ID reference at the end
                thread_ref = f"\n<!--conversation_id:{thread_id}-->"
                yield f"data: {json.dumps({'text': thread_ref})}\n\n"
                
            except Exception as e:
                error_msg = {"error": str(e)}
                yield f"data: {json.dumps(error_msg)}\n\n"
        
        # Use standard StreamingResponse with SSE format
        return StreamingResponse(
            stream_response(), 
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive", 
                "Content-Encoding": "identity"
            }
        )

    # New endpoint to retrieve conversation history
    @app.get(f"{base_path}/{{conversation_id}}/history")
    async def get_conversation_history(conversation_id: str):
        """Get message history for a conversation"""
        if not mongo_db.health_check():
            return {"messages": [], "error": "MongoDB not available"}
        
        messages = mongo_db.get_conversation_messages(conversation_id)
        return {"messages": messages}

    # New endpoint format using conversation_id in the path
    app.add_api_route(f"{base_path}/{{conversation_id}}/chat", chat_completions, methods=["POST"])
