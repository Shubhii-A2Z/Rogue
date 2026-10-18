from tools.paths import resolve_work_path
from tools.text import prepare_file_content
from langchain_core.tools import tool

@tool
def edit_file(path: str, old_str: str, new_str: str)->str:
    """
    Replaces `old_str` with `new_str` in the file at `path`.
    Language agnostic: .js, .java, .py and other text files all use the exact substring replace.
    Pass an empty `old_str` to create a new file (same as `write_file`).

    Args:
        path: Relative path of the file
        old_str: Exact String to be replaced. Empty string creates a new file.
        new_str: String to replace with
    """

    if not path or old_str==new_str:
        return f"Error: Invalid input"

    # Replacing literal \\n with actual newlines, or any markdown fences
    old_str=prepare_file_content(old_str, path)
    new_str=prepare_file_content(new_str, path)

    try:
        file_path=resolve_work_path(path)
    except ValueError as e:
        return f"Error: Path escapes working directory."
    
    # if old_str is empty, create a new file
    if old_str=="":
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(new_str, encoding="utf-8")
        return f"Created a new file {path!r}"
    
    try:
        old_content=file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error: Failed to read file {path!r} : {e}"
    
    # if old_str is not present in the file, return error message
    if old_str not in old_content:
        return f"Error: {path!r} does not contain {old_str!r}"
    
    # Replacing all occurrences of old_str with new_str
    new_content=old_content.replace(old_str, new_str)

    # Writing the new content to file
    file_path.write_text(new_content, encoding="utf-8")

    return f"Replaced {old_str!r} with {new_str!r} in {path!r}"
    
