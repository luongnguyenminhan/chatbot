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
        print(f"\n[API] Received chat request for conversation: {conversation_id}")
        print(f"[API] System prompt length: {len(request.system)} chars")
        print(f"[API] Number of tools: {len(request.tools)}")
        print(f"[API] Number of messages: {len(request.messages)}")
        
        inputs = convert_to_langchain_messages(request.messages)
        print(f"[API] Converted to {len(inputs)} LangChain messages")
        
        # Use conversation_id from URL path for thread persistence
        thread_id = conversation_id

        # Custom streaming implementation
        async def stream_response():
            """Stream response with proper Unicode handling"""
            print(f"\n[STREAM] Starting custom stream for conversation: {conversation_id}")
            
            # Pass thread_id to the graph configuration
            config = {
                "configurable": {
                    "system": request.system,
                    "frontend_tools": request.tools,
                    "thread_id": thread_id
                }
            }
            
            message_count = 0
            
            try:
                # Send initial message to make sure client receives headers
                yield "data: {}\n\n"
                
                async for msg, metadata in graph.astream(
                    {"messages": inputs},
                    config,
                    stream_mode="messages",
                ):
                    message_count += 1
                    print(f"\n[STREAM] Received message {message_count} of type: {type(msg).__name__}")
                    
                    if isinstance(msg, AIMessageChunk) or isinstance(msg, AIMessage):
                        if msg.content:
                            # Print full raw content for debugging
                            print(f"[STREAM] RAW CONTENT BEGIN >>>")
                            print(msg.content)
                            print(f"[STREAM] <<< RAW CONTENT END")
                            
                            # Print hex representation to debug encoding issues
                            print(f"[STREAM] HEX REPRESENTATION:")
                            print(''.join(f'\\x{ord(c):02x}' for c in msg.content[:50]))
                            
                            # Send as JSON to preserve Unicode
                            json_data = json.dumps({"text": msg.content})
                            print(f"[STREAM] JSON encoded: {json_data[:50]}...")
                            yield f"data: {json_data}\n\n"
                    
                    elif isinstance(msg, ToolMessage):
                        print(f"[STREAM] Tool message: {msg.tool_call_id}")
                        json_data = json.dumps({"tool": msg.tool_call_id, "result": msg.content})
                        yield f"data: {json_data}\n\n"
                
                # Add conversation ID reference at the end
                thread_ref = f"\n<!--conversation_id:{thread_id}-->"
                yield f"data: {json.dumps({'text': thread_ref})}\n\n"
                print(f"[STREAM] Stream completed, sent {message_count} messages")
                
            except Exception as e:
                print(f"[STREAM] ERROR during streaming: {str(e)}")
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

    # New endpoint format using conversation_id in the path
    app.add_api_route(f"{base_path}/{{conversation_id}}/chat", chat_completions, methods=["POST"])
    print(f"[API] Registered chat route at: {base_path}/{{conversation_id}}/chat")
