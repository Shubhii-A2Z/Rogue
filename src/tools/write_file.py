from tools.paths import resolve_work_path
from tools.text import prepare_file_content
from langchain.tools import tool

@tool
def write_file(path: str, content: str)->str:
    """
    Writes a file to the given path.

    Args:
        path: Path relative to the working directory.
        content: Content to write to the file.
    """

    if not path:
        return f"Error: Path is required"
    
    # Preparing the file content for writing to a file
    content=prepare_file_content(content, path)

    try:
        file_path=resolve_work_path(path) # Resolving the absolute path
    except ValueError as e:
        return f"Error: Path escapes working directory: {e}"
    
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True) # Creating the parent directory if it doesn't exists
        file_path.write_text(content, encoding="utf-8") # Writing the file content to the file
    except Exception as e:
        return f"Error: Failed to write file {path!r}: {e}"
    
    return f"File {path!r} written successfully."