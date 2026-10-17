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