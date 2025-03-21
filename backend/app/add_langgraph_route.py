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

        async def run(controller: RunController):
            print(f"[API] Starting streaming response for thread: {thread_id}")
            tool_calls = {}
            tool_calls_by_idx = {}

            # Pass thread_id to the graph configuration
            config = {
                "configurable": {
                    "system": request.system,
                    "frontend_tools": request.tools,
                    "thread_id": thread_id  # This enables memory persistence
                }
            }

            print(f"[API] Streaming from LangGraph with thread_id: {thread_id}")
            message_count = 0
            
            async for msg, metadata in graph.astream(
                {"messages": inputs},
                config,
                stream_mode="messages",
            ):
                message_count += 1
                print(f"[API] Received message {message_count} of type: {type(msg).__name__}")
                
                if isinstance(msg, ToolMessage):
                    print(f"[API] Tool message received for tool_call_id: {msg.tool_call_id}")
                    tool_controller = tool_calls[msg.tool_call_id]
                    tool_controller.set_result(msg.content)
                    print(f"[API] Tool result set: {msg.content[:50]}...")

                if isinstance(msg, AIMessageChunk) or isinstance(msg, AIMessage):
                    if msg.content:
                        print(f"[API] AI content chunk: {msg.content[:50]}...")
                        controller.append_text(msg.content)

                    if hasattr(msg, 'tool_call_chunks') and msg.tool_call_chunks:
                        print(f"[API] Tool call chunks: {len(msg.tool_call_chunks)}")
                        for chunk in msg.tool_call_chunks:
                            print(f"[API] Tool call: {chunk['name']}")
                            if not chunk["index"] in tool_calls_by_idx:
                                tool_controller = await controller.add_tool_call(
                                    chunk["name"], chunk["id"]
                                )
                                tool_calls_by_idx[chunk["index"]] = tool_controller
                                tool_calls[chunk["id"]] = tool_controller
                            else:
                                tool_controller = tool_calls_by_idx[chunk["index"]]

                            tool_controller.append_args_text(chunk["args"])

            # Add a hidden thread ID reference at the end of the response
            print(f"[API] Streaming complete, adding thread_id reference")
            controller.append_text(f"\n<!--conversation_id:{thread_id}-->")

        print(f"[API] Creating DataStreamResponse for conversation: {conversation_id}")
        return DataStreamResponse(create_run(run))

    # New endpoint format using conversation_id in the path
    app.add_api_route(f"{base_path}/{{conversation_id}}/chat", chat_completions, methods=["POST"])
    print(f"[API] Registered chat route at: {base_path}/{{conversation_id}}/chat")
