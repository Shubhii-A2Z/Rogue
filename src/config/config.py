import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Setting up the root directory for the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Setting up the prompts directory which will hold all the prompts
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# Setting up the default work directory for AI Coding Agent
DEFAULT_WORK_DIR = PROJECT_ROOT / "workspace"

AGENT_NAME = "Rogue Agent"

MAX_MODEL_CALLS_PER_RUN = int(os.getenv("MAX_MODEL_CALLS_PER_RUN","10"))

# Helper function to check if Human In The Loop (HITL) is enabled
def hitl_enabled()->bool:
    return os.getenv("HITL_ENABLED", "true") in {"1", "true", "yes"}


# Helper function to get the working directory
def get_working_directory()->Path:
    override=os.getenv("WORK_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve() # expanduser() used to expand the home directory path (~)
    return DEFAULT_WORK_DIR