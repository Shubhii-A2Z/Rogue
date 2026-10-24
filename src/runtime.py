from tools.text import prepare_file_content
from messages import last_tool_text
from messages import last_ai_message
from langgraph.types import Command
from typing import Any
from schemas import TurnSummary
from dataclasses import dataclass

@dataclass
class AgentTurnResult:
    text: str # represents agent's reply
    structured: TurnSummary # represents structured summary of the turn
    messages: list[Any]
    pending_interrupt: dict[str, Any] | None


def start_turn(agent, user_text: str, config: dict)->AgentTurnResult:
    """
    Executes one turn of the agent with the given user input and configuration
    with real-time streaming of messages.
    """

    print("\nRogue: ", end="", flush=True)

    # Only stream conversational content (skip internal tool call tokens)
    for chunk, _ in agent.stream(
        {
            "messages": [
                {"role": "user", "content": user_text}
            ]
        },
        config=config,
        stream_mode="messages",
    ):
        if chunk.content and not getattr(chunk, "tool_call_chunks", None):
            print(chunk.content, end="", flush=True)
    
    print()

    # Retrieve current state to check for interrupts or messages
    state=agent.get_state(config)

    # Parsing the result of agent invocation.
    return parse_state_result(state)


def _as_summary(value: Any)->TurnSummary | None:
    """
    Creates a TurnSummary from the given value.
    """
    if value is None:
        return None
    if isinstance(value, TurnSummary):
        return value
    if isinstance(value, dict):
        try:
            return TurnSummary.model_validate(value)
        except Exception:
            return None
    return None


def parse_state_result(state: Any)->AgentTurnResult:
    """
    Parse a state snapshot from agent.get_state(config) to extract messages and interrupts.
    """

    # Extracting interrupts directly from the tasks
    interrupts=[]
    for task in getattr(state, "tasks", ()):
        for interrupt in getattr(task, "interrupts", ()):
            interrupts.append(interrupt)

    # Get the complete graph state using the value property
    value=getattr(state, "value", {})
    if not isinstance(value, dict):
        value={}
    
    messages=value.get("messages") or []

    # If there are interrupts, it means that the agent is waiting for user input.
    if interrupts:
        payload=interrupts[0].value
        return AgentTurnResult(
            text="",
            structured=None,
            messages=messages,
            pending_interrupt=payload if isinstance(payload, dict) else {"raw": payload}
        )

    # No interrupts, agent completed normally.
    return AgentTurnResult(
        text=last_ai_message(messages) or last_tool_text(messages),
        messages=messages,
        pending_interrupt=None,
        structured=_as_summary(value.get("structured_response"))
    )


def resume_turn(agent, decisions: list[dict], config: dict)->AgentTurnResult:
    """
    Resumes an interrupted turn, during human-in-the-loop, using the provided decisions from user.
    """

    print("\nRogue: ", end="", flush=True)
    
    for chunk, _ in agent.stream(
        Command(
            resume={
                "decisions": decisions
            }
        ),
        config=config,
        stream_mode="messages"
    ):
        if chunk.content and not getattr(chunk, "tool_call_chunks", None):
            print(chunk.content, end="", flush=True)
    
    print()

    # Retrieve current state to check for interrupts or messages
    state=agent.get_state(config)

    # Parsing the result of agent invocation.
    return parse_state_result(state)


def format_interrupt_payload(payload: dict[str, Any])->str:
    """
    Formats the payload of an interrupt for display.

    This function takes the payload dictionary from an interrupt and formats it into a human-readable string.
    """

    # Getting list of actions requested by agent
    requests=payload.get("action_requests", [])
    lines=[]

    for index, action in enumerate(requests, start=1):
        name=action.get("name", "") # Extracts the tool name
        args=dict(action.get("args", {})) # Extract arguments/parameters in format {"argument": "value"}
        description=action.get("description", "") # Extract explanation of why the interrupt was triggered.

        # For each action, creates a formatted string showing the tool name, description, and arguments
        lines.append(f"{index}. {name} ({description})")

        for key, value in args.items():
            preview=str(value)

            # If tool call is any of write_file or edit_file
            if key in {"content", "old_str", "new_str"}:
                preview=prepare_file_content(preview, str(args.get("path", "")))
            
            if "\n" in preview:
                lines.append(f"   {key}:")
                for body_line in preview.splitlines():
                    lines.append(f"     {body_line}")
                continue
            
            # Truncate long values for better readability
            if len(preview)>240:
                preview=preview[:240]+"..."
            
            lines.append(f"     {key}: {preview}")
        
    return "\n".join(lines) if lines else str(payload)