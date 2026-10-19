from runtime import start_turn
from runtime import resume_turn
from runtime import AgentTurnResult
from runtime import format_interrupt_payload
from typing import Any
from prompts import build_greeting_prompt
from models import select_provider
from config import get_working_directory
from memory import thread_config, make_checkpointer
from agent import build_agent
import uuid


def ask_approval(tool_name: str)->bool:
    """
    This function is used to ask for the user's approval for a tool call.
    """
    while True:
        response=input(f"Approve {tool_name}? (y/n): ").strip().lower()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        else:
            print("Please answer with 'y' (yes) or 'n' (no).", flush=True)


def prompt_decision(pending_interrupt: dict[str, Any])->list[dict]:
    """
    This function is used to prompt the user for a decision on the pending interrupt.
    """
    print("\n---- Human-In-The-Loop -----", flush=True)
    print(format_interrupt_payload(pending_interrupt), flush=True)

    requests=pending_interrupt.get("action_requests", [])
    decisions: list[dict]=[]

    for action in requests:
        tool_name=action.get("name", "tool")
        approved=ask_approval(tool_name)

        if approved:
            decisions.append({
                "type": "approve"
            })
        else:
            decisions.append({
                "type": "reject",
                "message": f"User declined {tool_name}"
            })
    
    return decisions


def drain(agent, result: AgentTurnResult, config: dict)->AgentTurnResult:
    """
    This function is used to process the pending interrupts of the agent.
    """
    while result.pending_interrupt is not None:
        decision=prompt_decision(result.pending_interrupt)
        result=resume_turn(agent, decision, config)
    return result


def chat()->None:
    working_directory=get_working_directory()
    working_directory.mkdir(parents=True, exist_ok=True)

    provider=select_provider()

    checkpointer=make_checkpointer()

    agent=build_agent(checkpointer=checkpointer)
    config=thread_config(str(uuid.uuid4()))

    print(build_greeting_prompt())
    print(f"Provider: {provider.name} . {provider.model}")
    print(f"Working Directory: {working_directory}")
    print("Type 'exit', 'quit' to stop.")

    while True:
        user_input=input("You: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            break
        
        if not user_input:
            continue

        try:
            result=drain(agent, start_turn(agent, user_input, config), config)
        except RuntimeError as e:
            print(f"Agent: {e}\n")
            continue
        except Exception as e:
            print(f"Agent: {type(e).__name__}: {e}\n")
            continue
        
        if result.structured:
            print(
                f"  Summary: {result.structured.status}\n"
                f"{result.structured.summary} "
                f"Files touched: {result.structured.files_touched}"
            )


if __name__=='__main__':
    chat()