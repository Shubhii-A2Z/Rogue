from langchain.agents.middleware import HumanInTheLoopMiddleware

def built_hitl_middleware()->HumanInTheLoopMiddleware:
    """Builds a HumanInTheLoopMiddleware for the coding agent."""
    
    return HumanInTheLoopMiddleware(
        interrupt_on={
            "read_file": False, # No HITL required for read_file tool
            "list_files": False, # No HITL required for list_files tool
            "write_file": {
                "allowed_decisions": ["approve", "edit", "reject"],
                "description": "Write or overwrite a file on disk"
            },
            "edit_file": {
                "allowed_decisions": ["approve", "edit", "reject"],
                "description": "Edit an existing file on disk"
            }
        },
        description_prefix="Coding Agent needs your approval to move ahead"
    )