import json
from config.config import get_working_directory
from datetime import UTC
from datetime import datetime
from typing import Any
from collections.abc import Callable

from langgraph.types import Command
from langchain.tools.tool_node import ToolMessage
from langchain.agents.middleware import AgentMiddleware, ToolCallRequest

class AuditMiddleware(AgentMiddleware):
    """Append a JSON record after each tool call (allowed or denied)"""

    def wrap_tool_call(
        self,
        request: ToolCallRequest, # Request represents the tool call
        handler: Callable[[ToolCallRequest], ToolMessage| Command] # The next middleware, which can be another tool call, Tool Message or command
    )->ToolMessage | Command:

        result=handler(request) # Run the next middleware in the chain
        preview=""

        if isinstance(result, ToolMessage):
            preview=str(result.content)[:200]
        
        # JSON we want to log
        self.write({
            "timestamp": datetime.now(UTC).isoformat(),
            "tool": request.tool_call.get("name"),
            "result_preview": preview,
            "arguments": request.tool_call.get("args")
        })

        return result
    

    def write(
        self,
        entry: dict[str, Any]
    )->None:

        # Path of log file
        log_path=get_working_directory() / ".agent_audit.log"
        # Ensuring parent directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Opening the log file in append mode and write the entry
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry)+"\n")
