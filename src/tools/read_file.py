from langchain_core.tools import tool
from tools.paths import resolve_work_path

@tool
def read_file(path: str)->str:
    """
    Reads a UTF-8 text file from the working directory

    Args:
        path: Relative path of the file
    """

    try:
        file_path=resolve_work_path(path)
    except ValueError as e:
        return f"Path escapes working directory: {e}"
    
    try:
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"File not found: {path}"
    except Exception as e:
        return f"Error reading the file: {e}"