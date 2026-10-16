from tools.shell import stop_job
from tools.shell import list_jobs
from tools.shell import run_command
from tools.list_files import list_files
from tools.read_file import read_file

ALL_TOOLS=[
    read_file,
    list_files,
    run_command,
    list_jobs,
    stop_job,
]


def tool_catalog()->list[dict[str, str]]:
    """
    Returns a list of all available tools with their descriptions.
    """
    
    return [{"name": tool.name, "description": tool.description} for tool in ALL_TOOLS]