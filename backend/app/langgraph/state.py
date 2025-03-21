from typing import Annotated, List, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # The add_messages annotation ensures proper handling of message history for conversation memory
    messages: Annotated[list, add_messages]
    # RAG context storage for retrieved knowledge
    rag_context: Optional[List[str]]
