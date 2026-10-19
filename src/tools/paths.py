from fnmatch import fnmatch
from pathlib import Path
from config.config import get_working_directory


# blocking certain paths from being accessed by the AI Coding Agent
BLOCKED_PATH_PATTERNS=[
    ".env",
    ".env.*",
    ".pem",
    ".secret",
    ".git",
    ".git/**",
    "*.log",
    "*.p12",
]


def normalize_path(path: str)->str:
    normalized=Path(path).as_posix() # Convert Path object to a posix-style path (e.g., 'folder/file.txt' instead of 'folder\file.txt')
    if normalized.startswith("./"):
        normalized=normalized[2:] # Removing the leading './' if it exists
    return normalized


def is_blocked_path(path: str)->bool:
    normalized=normalize_path(path)
    return any(fnmatch(normalized, pattern) for pattern in BLOCKED_PATH_PATTERNS) # checking if the path matches any of the blocked patterns


def resolve_work_path(path: str)->Path:
    work_dir=get_working_directory()
    work_dir.mkdir(parents=True, exist_ok=True) # Creating the working directory if it doesn't exists
    candidate=(work_dir / path).resolve() # Resolving absolute path

    try:
        candidate.relative_to(work_dir) # Checking if the candidate path is inside the working directory
    except ValueError as e:
        raise ValueError("Path escapes working directory")

    return candidate