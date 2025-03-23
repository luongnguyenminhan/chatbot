from fastapi.responses import StreamingResponse
import json
import json
from typing import List, Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.messages import (
    HumanMessage,
    AIMessageChunk,
    AIMessage,
    ToolMessage,
    SystemMessage,
    BaseMessage,
)

from .database.mongo_client import mongo_db
from .models import (
    LanguageModelV1Message,
    LanguageModelTextPart,
    LanguageModelImagePart,
    LanguageModelToolCallPart,
    ChatRequest
)


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

        if tool_info:
            message_data["tool_info"] = tool_info

        mongo_db.save_message(conversation_id, message_data)
        return True
    return False


def add_langgraph_route(app: FastAPI, graph, base_path: str):
    async def chat_completions(conversation_id: str, request: ChatRequest):

        inputs = convert_to_langchain_messages(request.messages)

        for msg in request.messages:
            if msg.role == "user":
                text_content = ""
                for part in msg.content:
                    if isinstance(part, LanguageModelTextPart):
                        text_content += part.text

                if text_content:
                    save_message_to_mongodb(conversation_id, "user", text_content)

        thread_id = conversation_id

        async def stream_response():
            """Stream response with proper Unicode handling"""

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
                            json_data = json.dumps({"text": msg.content})
                            yield f"data: {json_data}\n\n"

                            full_response += msg.content

                    elif isinstance(msg, ToolMessage):
                        json_data = json.dumps({"tool": msg.tool_call_id, "result": msg.content})
                        yield f"data: {json_data}\n\n"

                        save_message_to_mongodb(
                            conversation_id,
                            "tool",
                            msg.content,
                            {"tool_call_id": msg.tool_call_id}
                        )

                if full_response:
                    clean_response = full_response.replace(f"\n<!--conversation_id:{thread_id}-->", "")
                    save_message_to_mongodb(conversation_id, "assistant", clean_response)

                thread_ref = f"\n<!--conversation_id:{thread_id}-->"
                yield f"data: {json.dumps({'text': thread_ref})}\n\n"

            except Exception as e:
                error_msg = {"error": str(e)}
                yield f"data: {json.dumps(error_msg)}\n\n"

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Encoding": "identity"
            }
        )

    @app.get(f"{base_path}/{{conversation_id}}/history")
    async def get_conversation_history(conversation_id: str):
        """Get message history for a conversation"""
        if not mongo_db.health_check():
            return {"messages": [], "error": "MongoDB not available"}

        messages = mongo_db.get_conversation_messages(conversation_id)
        return {"messages": messages}

    app.add_api_route(f"{base_path}/{{conversation_id}}/chat", chat_completions, methods=["POST"])
