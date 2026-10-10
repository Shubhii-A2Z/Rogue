from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_core.messages import ToolMessage
from langchain_core.messages import AIMessage
from typing import Any


def user_input(text: str)->dict[str, str]:
    """Builds OpenAI style dictionary for user input"""
    return {"role": "user", "content": text}


def last_ai_message(messages: list[Any])->str:
    """Finds the last AI message that is not a tool call"""
    for message in reversed(messages):

        # skip non AI messages
        if not isinstance(message, AIMessage):
            continue
        
        # skip messages with tool calls
        if getattr(message, "tool_calls", None):
            continue
        content=message.content

        # handle simple string message
        if isinstance(content, str):
            return content
        
        # handle list content
        if isinstance(content, list):
            parts=[
                p["text"] for p in content if p.get("type")=="text"
            ]
            if parts:
                return "\n".join(parts)
    return ""


def last_tool_text(messages: list[Any])->str:
    """Finds the content of last tool call result."""
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            content=message.content
            return content if isinstance(content, str) else str(content)
    return ""


def describe_message(message)->str:
    """Returns a single-line summary of the message suitable for display. Useful for logging"""

    # Get the role from the message type (e.g., AIMessage -> ai)
    role=type(message).__name__.replace("Message", "").lower()
    content=message.content
    preview=content if isinstance(content, str) else str(content)
    preview.replace("\n", " ")

    extra=""

    # AI messages with tool calls
    if isinstance(message, AIMessage) and message.tool_calls:
        names=", ".join(call.get("name", "?") for call in message.tool_calls)
        extra=f" tools=[{names}]"

    # Tool messages
    if isinstance(message, ToolMessage):
        extra=f" tool_call_id={message.tool_call_id}"

    # System messages
    if isinstance(message, SystemMessage):
        extra=" (system)"

    # Human messages
    if isinstance(message, HumanMessage):
        extra=f" (human)"
    
    return f"{role}{extra}: {preview}"