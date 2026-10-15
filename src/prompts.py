from config.config import get_working_directory
from config.config import AGENT_NAME
from config.config import PROMPTS_DIR
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Configure the Jinja2 environment used to load and render prompt templates.
_env=Environment(
    loader=FileSystemLoader(PROMPTS_DIR), # Loads templates from the prompts directory
    autoescape=select_autoescape(enabled_extensions=()), # Disables auto escaping
    trim_blocks=True, # Removes leading whitespaces
    lstrip_blocks=True # Removes trailing whitespaces
)


def render_template(template_name: str, **context)->str:
    """
    Load a Jinja2 template and render it with the provided context.

    Args:
        template_name: Name of the template file inside PROMPTS_DIR.
        **context: Named variables passed to the template for rendering.

    Returns:
        The rendered template as a string.
    """
    return _env.get_template(template_name).render(**context)


def build_system_prompt(
    *,
    agent_name: str=AGENT_NAME,
    extra_guidance: str=""
)->str:
    """
    Build the system prompt that defines the AI agent's behavior.

    Provides the agent's name, working directory, and any additional
    instructions to the system.jinja template.

    Args:
        agent_name: Name used to identify the AI agent.
        extra_guidance: Optional additional instructions for the agent.

    Returns:
        The rendered system prompt as a string.
    """
    return render_template("system.jinja", agent_name, extra_guidance, str(get_working_directory()))


def build_greeting_prompt(
    *,
    agent_name: str=AGENT_NAME,
)->str:
    """
    Build the greeting prompt used for the AI agent's introduction.

    Provides the agent's name and working directory to the
    greetings.jinja template.

    Args:
        agent_name: Name used to identify the AI agent.

    Returns:
        The rendered greeting prompt as a string.
    """
    return render_template("greetings.jinja", agent_name, str(get_working_directory()))