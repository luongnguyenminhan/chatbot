from pydantic import BaseModel, Field
from typing import List, Literal, Union, Optional, Dict, Any
from datetime import datetime

# ---------- Conversation Models ----------
class Conversation(BaseModel):
    conversation_id: str
    title: Optional[str] = "New Conversation"
    created_at: str
    updated_at: str


class ConversationCreate(BaseModel):
    conversation_id: str
    title: Optional[str] = "New Conversation"


class ConversationUpdate(BaseModel):
    title: Optional[str] = None


# ---------- Message Models ----------
class MessageBase(BaseModel):
    conversation_id: str
    role: str
    content: str
    timestamp: Optional[str] = None


class MessageCreate(MessageBase):
    pass


class MessageResponse(MessageBase):
    id: Optional[str] = None
    tool_info: Optional[Dict[str, Any]] = None


# ---------- Language Model Message Parts ----------
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


# ---------- Message Models ----------
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


# ---------- Tool and Chat Models ----------
class FrontendToolCall(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: dict[str, Any]


class ChatRequest(BaseModel):
    system: Optional[str] = ""
    tools: Optional[List[FrontendToolCall]] = []
    messages: List[LanguageModelV1Message]
    # No thread_id field since it comes from path parameter


class AnyArgsSchema(BaseModel):
    # By not defining any fields and allowing extras,
    # this schema will accept any input passed in.
    class Config:
        extra = "allow"


# ---------- API Response Models ----------
class StatusResponse(BaseModel):
    status: str
    message: str


class HealthCheckResponse(BaseModel):
    status: str
    mongodb: bool


class ConversationHistoryResponse(BaseModel):
    messages: List[Dict[str, Any]]
    error: Optional[str] = None
