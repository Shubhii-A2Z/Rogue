import subprocess
import re
import sys
import shlex
import os
from config.config import get_working_directory

MAX_OUTPUT_CHARS=8000
DEFAULT_TIMEOUT=30

# blocks execution of dangerous commands
BLOCKED_COMMAND_PATTERNS=(
    r"\bsudo\b",
    r"\bmkfs\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bchmod\s+777\b",
)

# Commands to run servers
SERVER_PATTERN=(
    r"\buvicorn\b",
    r"\bgunicorn\b",
    r"\bhypercorn\b",
    r"\bpython[0-9.]*\s+\S*app\.py\b",
    r"\bnpm\s+start\b",
    r"\bnpx\s+(serve|next|vite|nuxt)\b",
    r"\bstreamlit\s+run\b",
    r"\bflask(\s+--app)?\s+run\b",
)


def deny_command(command: str)->str | None:
    # Removing leading/trailing whitespace
    stripped=command.strip()

    if not stripped:
        return "Blocked by middleware: command is empty"
    
    # Checking against Blocked Command Patterns
    for pattern in BLOCKED_COMMAND_PATTERNS:
        if re.search(pattern, stripped, flags=re.IGNORECASE):
            return f"Blocked by middleware: {command} matches dangerous pattern {pattern}"
    
    # The command is safe and can proceed
    return None


def looks_like_server(command: str)->bool:
    return any(re.search(pattern, command, flags=re.IGNORECASE) for pattern in SERVER_PATTERN)


# Python specific package management patterns, so as to replace global pip with pip of our virtual environment (pip install -> venv/bin/python -m pip install)
_PIP_PREFIX=re.compile(r"^(?:pip[0-9.]*|python[0-9.]*\s+-m\s+pip)\b", re.IGNORECASE)

_FLASK_PREFIX=re.compile(r"^flask\b", re.IGNORECASE)

# Replacing global =ly installed python with python of our virtual environment (python run -> venv/bin/python run)
_PYTHON_PREFIX=re.compile(r"^python[0-9.]*\b", re.IGNORECASE)


def rewrite_command(command: str)->str:

    # Path to the executable of current Python virtual environment
    exec=shlex.quote(sys.executable)

    stripped=command.strip()

    # Check if command matches pip prefix
    if _PIP_PREFIX.match(stripped):
        return _PIP_PREFIX.sub(f"{exec} -m pip", stripped, count=1)
    
    if _PYTHON_PREFIX.match(stripped):
        return _PYTHON_PREFIX.sub({exec}, stripped, count=1)

    if _FLASK_PREFIX.match(stripped):
        return _FLASK_PREFIX.sub(f"{exec} -m flask", stripped, count=1)
    
    return stripped


def _clip(text: str)->str:
    if len(text)<=MAX_OUTPUT_CHARS:
        return text
    return text[-MAX_OUTPUT_CHARS:]+"\n... (truncated)"


def _run_foreground(command: str, timeout: int)->str:
    """Running short-lived commands like 'ls', 'pwd', 'cat', 'echo' etc"""

    current_working_directory=get_working_directory()
    current_working_directory.mkdir(parents=True, exist_ok=True)

    # Loading accessible environment variables in form of a dictionary
    env=os.environ.copy()
    # Setting buffer to 1, so that output is not buffered and shown immediately
    env.setdefault("PYTHONUNBUFFERED", "1")

    try:
        completed=subprocess.run(
            ["/bin/bash", "-lc", command], # Using bash to execute the command, -l for login shell, -c for command
            cwd=current_working_directory,
            env=env,
            timeout=timeout,
            capture_output=True, # Capture stdout/stderr
            text=True # Decode stdout/stderr as text
        )
    except subprocess.TimeoutExpired as e:
        stdout=(e.stdout or "") + (e.stderr or "")
        return (
            f"Timed out after {timeout}s (process killed)."
            f"If this is a server, re-run with background=True."
            f"{_clip(str(stdout))}"
        )
    
    # Command completed successfully
    chunks=[]
    if completed.stdout:
        chunks.append(completed.stdout.rstrip())
    if completed.stderr:
        chunks.append(completed.stderr.rstrip())
    
    body="\n".join(chunks) if chunks else "No output."
    return f"exit_code: {completed.returncode}\ncwd={current_working_directory}\n{_clip(body)}"
    
