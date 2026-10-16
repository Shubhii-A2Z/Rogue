from tools.jobs import is_running
from tools.jobs import all_jobs
from langchain_core.tools import tool
from tools.jobs import read_log_tail
from tools.jobs import stop_job
import time
from tools.jobs import BackgroundJob
from tools.jobs import register
from datetime import UTC
from datetime import datetime
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


def _run_background(command: str)->str:
    """Running long-lived servers e.g. python app.py"""

    current_working_directory=get_working_directory()
    current_working_directory.mkdir(parents=True, exist_ok=True)

    # Loading accessible environment variables in form of a dictionary
    env=os.environ.copy()
    # Setting buffer to 1, so that output is not buffered and shown immediately
    env.setdefault("PYTHONUNBUFFERED", "1")

    log_dir=current_working_directory / ".agent_jobs"
    log_dir.mkdir(parents=True, exist_ok=True)

    current_timestamp=datetime.now(UTC).isoformat()
    current_timestamp=current_timestamp.replace(":", "").replace("+", "")

    # Creates a temporary log file with prefix 'pending' and timestamp
    temp_log=log_dir / f"pending-{current_timestamp}.log"
    # Opening the temporary log file in write mode with UTF-8 encoding
    log_file=temp_log.open('w', encoding="utf-8")

    try:
        process=subprocess.Popen(
            ["/bin/bash", "-lc", command],
            cwd=current_working_directory,
            env=env,
            stdout=log_file, # Redirect standard output to log file
            stderr=subprocess.STDOUT, # Redirect standard error to standard output
            start_new_session=True # Starts a new session for every command
        )
    finally:
        log_file.close()

    # Creating a permanent log file with processId as unique identifier
    log_path=log_dir / f"{process.pid}.log"
    # Rename the temporary log file to permanent log file
    temp_log.rename(log_path)

    # Register the background job
    register(
        BackgroundJob(
            processId=process.pid,
            bash_command=command,
            log_path=log_path,
            started_at=datetime.now(UTC).isoformat(),
            process=process
        )
    )

    time.sleep(1)

    tail=read_log_tail(log_path)
    if process.poll() is not None:
        stop_job(process.pid)
        return (
            f"Background command exited immediately (process_id={process.pid})"
            f"exit_code: {process.returncode}\n{_clip(tail)}"
        )
    
    # finds any URLs in the log file
    urls=re.findall(r"https?://[^\s]+", tail)

    url_line=f"Open in browser: {urls[0]}\n" if urls else (
        "No url in the log yet - try http://127.0.0.1:3000"
        "and check list_jobs if it is blank.\n"
    )

    return (
        f"{url_line}\n"
        f"Started background job (pid={process.pid}).\n"
        f"Log: {log_path}\n"
        f"cwd: {current_working_directory}\n"
        f"--------output so far------\n{_clip(tail)}"
    )


@tool
def stop_job(pid: int)->str:
    """
    Stop a background job previously started by run_command.
    Args:
        pid: The process id of job to stop
    """

    return stop_job(pid)


@tool
def run_command(command: str, background: bool=False, timeout_seconds: int=0)->str:
    """
    Run a bash command in the working directory (host machine, not a sandbox).
    Foreground commands wait for completion. Set background=True for server like (flask, uvicorn, npm start)
    so they keep running. Server-like commands are auto backgrounded even if you forget the flag.

    Args:
        command: bash command to run e.g. 'python app.py' or 'ls -la'.
        background: If true, start the process and run pid immediately.
        timeout_seconds: Maximum time to wait for the command to complete. This is for foreground timeout. 0 uses default of 30s.
    """

    blocked=deny_command(command)
    if blocked:
        return blocked
    
    timeout_seconds=timeout_seconds if timeout_seconds>0 else DEFAULT_TIMEOUT

    # Check if the command is a background job
    background_job=bool(background) or looks_like_server(command)

    # Rewriting the command to use the virtual environment's python/pip
    command=rewrite_command(command)

    if background_job:
        return _run_background(command)
    else:
        return _run_foreground(command, timeout_seconds)


@tool
def list_jobs()->str:
    """
    List all background jobs started by run_command.
    """

    jobs=all_jobs()
    if not jobs:
        return "No background jobs running."
    
    lines=[]
    for job in jobs:
        state="running" if is_running(job.processId) else "exited"
        lines.append(
            f"pid: {job.processId} state: {state} started: {job.started_at} command: {job.bash_command}"
        )

        tail=read_log_tail(job.log_path, max_chars=800)

        if tail:
            lines.append(tail.rstrip())
            lines.append("-----------------------")
    
    # Joining all lines with newline character
    return "\n".join(lines)