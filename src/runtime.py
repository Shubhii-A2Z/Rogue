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
    Executes one turn of the agent with the given user input and configuration.
    """
    result=agent.invoke(
        {
            "messages": [
                {"role": "user", "content": user_text}
            ]
        },
        config=config,
        version= "v2"
    )

    # Parsing the result of agent invocation.
    return parse_invoke_result(result)


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


def parse_invoke_result(result: Any)->AgentTurnResult:
    """
    Parse the result of an agent invocation, extracting the agent's reply.
    If the result contains an interruption (e.g. for human-in-the-loop),
    this will be exposed in the `interrupts` field.
    """
    interrupts=tuple(getattr(result, "interrupts",()), ())

    # Get the complete graph state using the value property
    value=getattr(result, "value", result)
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
    result=agent.invoke(
        Command(
            resume={
                "decisions": decisions
            }
        ),
        config=config,
        version="v2"
    )

    # Parsing the result of agent invocation.
    return parse_invoke_result(result)