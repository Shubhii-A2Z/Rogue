import os

from dataclasses import dataclass
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

@dataclass(frozen=True)
class Provider:
    """
    Represents one LLM provider as DATA.

    Instead of scattering provider information throughout
    the code, we keep everything related to a provider
    inside this simple class.

    Example:
        Provider(
            name="Groq",
            env_var="GROQ_API_KEY",
            is_free=True,
            base_url=None,
            model="openai/gpt-oss-20b"
        )

    frozen=True means that once a Provider object is created,
    its values cannot be changed accidentally.
    """

    name: str
    env_var: str
    is_free: bool
    base_url: str | None
    model: str

PROVIDERS=[
    Provider("Groq", "GROQ_API_KEY", True, None, "openai/gpt-oss-20b"),
]


def select_provider()->Provider:
    """
    Find which LLM provider is configured.

    The function checks each provider and asks:

        "Does the required API key exist?"

    The first provider with a valid API key is selected.

    This means our application doesn't need to know
    which provider the user configured.
    """
    for provider in PROVIDERS:
        if os.environ.get(provider.env_var):
            return provider
    expected=", ".join(p.env_var for p in PROVIDERS)
    raise RuntimeError(f"No provider key set. Add one of {expected} to your .env file")


def build_chat_model()->tuple[ChatGroq, Provider]:
    """
    Builds and returns a ChatGroq client along with the selected provider configuration.

    This function selects the appropriate LLM provider based on environment variables and
    initializes the ChatGroq client with the necessary configuration.

    Returns:
        tuple[ChatGroq, Provider]: A tuple containing the initialized ChatGroq client and the selected provider.
    
    Raises:
        RuntimeError: If no provider keys are set in the environment variables.
    """
    provider=select_provider()

    kwargs: dict={
        "model": provider.model,
        "api_key": os.getenv(provider.env_var)
    }

    if provider.base_url is None:
        kwargs["base_url"]=provider.base_url
    
    return ChatGroq(**kwargs), provider