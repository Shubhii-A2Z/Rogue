from schemas import TurnSummary
from langchain.agents.structured_output import ProviderStrategy
from prompts import build_system_prompt
from config.config import hitl_enabled
from models import build_chat_model
from middlewares.hitl import built_hitl_middleware
from middlewares.protection import ProtectionMiddleware
from middlewares.audit import AuditMiddleware
from config.config import MAX_MODEL_CALLS_PER_RUN
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain.agents import create_agent


def build_middleware(
    *,
    enable_hitl: bool
)->list:
    """
    Build the middleware layers used to control and protect the agent.

    The middleware list includes a model-call limit, audit logging,
    and payload protection. Human-in-the-loop approval middleware
    is added only when enable_hitl is True.

    Args:
        enable_hitl: Whether to enable human approval for actions
            handled by the HITL middleware.

    Returns:
        A list of configured middleware instances.
    """

    layers: list=[
        ModelCallLimitMiddleware(run_limit=MAX_MODEL_CALLS_PER_RUN, exit_behavior="end"),
        AuditMiddleware(),
        ProtectionMiddleware(),
    ]

    # Add human approval middleware only when explicitly enabled
    if enable_hitl:
        layers.append(built_hitl_middleware())

    return layers


def build_agent(
    *,
    enable_hitl: bool | None=None,
    extra_guidance: str=""
):
    """
    Create and configure the coding agent.

    Builds the chat model, prepares the system prompt, configures
    middleware, and sets the structured response format.

    If enable_hitl is None, the default HITL setting is read from
    the environment variable. Otherwise, the supplied value
    overrides that default.

    Args:
        enable_hitl: Whether to enable HITL middleware. Use None
            to follow the configured default.
        extra_guidance: Optional additional instructions appended
            through the system prompt template.

    Returns:
        A configured LangChain agent ready to process requests.
    """

     # Create the chat model and retrieve its provider information.
    model, _provider=build_chat_model()

    # take value of environment variable if enable_hitl is not provided, else use value of enable_hitl
    use_hitl=hitl_enabled() if enable_hitl is None else enable_hitl

    # Combine the model, instructions, middleware, and output schema.
    return create_agent(
        model=model,
        system_prompt=build_system_prompt(extra_guidance=extra_guidance),
        middleware=build_middleware(enable_hitl=use_hitl),
        response_format=ProviderStrategy(TurnSummary),
        name="Coding Agent"
    )