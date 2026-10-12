import re

from tools.paths import resolve_work_path
from tools.paths import is_blocked_path
from typing import Any
from collections.abc import Callable

from langgraph.types import Command
from langchain.tools.tool_node import ToolMessage
from langchain.agents.middleware import AgentMiddleware, ToolCallRequest


BLOCKED_EDIT_PATTERNS=(
    r"\bos\.system\s*\(",
    r"\bsubprocess\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"__import__\s*\("
)

_FILE_TOOLS={"read_file", "edit_file", "write_file", "list_files"}

def deny_reason(tool_name: str, arguments: dict[str, Any])->str | None:
    """Returns None if tool call is allowed, or a reason if it should be denied"""

    if tool_name not in _FILE_TOOLS:
        return None
    
    path=arguments.get("path", ".")

    if is_blocked_path(str(path)):
        return f"Blocked by middleware: access to protected path {path} is not allowed."

    if tool_name=="read_file":
        try:
            file_path=resolve_work_path(str(path))
        except ValueError as e:
            return f"Blocked by middleware: {e}"
        
        if file_path.is_file() and file_path.stat().st_size> 1024*1024*10: # 10 MB
            return f"Blocked by middleware: file {file_path} is too large to read."
    
    payload=""
    if tool_name=="edit_file":
        payload=str(arguments.get("new_str", ""))
    elif tool_name=="write_file":
        payload=str(arguments.get("content", ""))
    
    if payload:
        for pattern in BLOCKED_EDIT_PATTERNS:
            if re.search(pattern, payload):
                return f"Blocked by middleware: suspicious payload contains {pattern!r}"

    return None


def _tool_message(request: ToolCallRequest, reason: str)->ToolMessage:
    return ToolMessage(
        content=reason,
        tool_call_id=request.tool_call.get("id"),
        name=request.tool_call.get("name")
    )


class ProtectionMiddleware(AgentMiddleware):
    """Short circuit tool calls that target secrets or dangerous payloads"""

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command]
    )->ToolMessage | Command:

        name=request.tool_call.get("name", "")
        arguments=request.tool_call.get("args", {})

        reason=deny_reason(name, arguments)

        if reason:
            return _tool_message(request, reason)
        return handler(request) # else continue with the tool call