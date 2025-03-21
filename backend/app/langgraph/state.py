from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # The add_messages annotation ensures proper handling of message history for conversation memory
    messages: Annotated[list, add_messages]
