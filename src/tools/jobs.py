from pathlib import Path
import os
import subprocess
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from datetime import UTC, datetime
import signal
import contextlib


@dataclass
class BackgroundJob:
    """Represents a background job started by the agent."""

    processId: int
    bash_command: str
    started_at: str
    log_path: str
    process: Any=field(default=None, repr=False)


_JOBS: dict[int, BackgroundJob]=()


def register(job: BackgroundJob)->None:
    """Register a new background job."""

    _JOBS[job.processId]=job


def get_job(pid: int)->BackgroundJob | None:
    """Get a background job by its process ID."""

    return _JOBS.get(pid)


def all_jobs()->list[BackgroundJob]:
    """Return list of all background jobs."""

    return list(_JOBS.values())


def remove_job(pid: int)->BackgroundJob | None:
    """Remove a background job by its process ID."""

    return _JOBS.pop(pid, None)


def is_running(pid: int)->bool:
    """Check if process with given pid is running."""

    job=get_job(pid)

    # if the process was started through subprocess, check if it is still running
    if job is not None and job.process is not None:
        return job.process.poll() is None # if poll() returns None, it means the process is still running, else means process has exited with some return code
    
    # otherwise check if process with given pid is running using os.kill
    try:
        os.kill(pid, 0) # Signal 0 checks if process is running without sending a signal
        return True
    except OSError:
        return False


def stop_job(pid: int)->str:
    """Stop a background job by its process ID."""

    job=get_job(pid)
    if job is None:
        return f"Error: {pid} is not a job started by the agent."
    
    if not is_running(pid):
        if job.process is not None:
            with contextlib.suppress(ChildProcessError):
                job.process.wait(timeout=0.1) # cleanup zombie child process
        
        remove_job(pid)
        return f"Job {pid} is already stopped."
    
    try:
        os.killpg(pid, signal.SIGTERM) # Sending SIGTERM signal to the process group to terminate it
    except ProcessLookupError:
        remove_job(pid)
        return f"Job {pid} is already stopped."
    except PermissionError as e:
        return f"Error stopping job {pid}: {e}"
    
    if job.process is not None:
        try:
            job.process.wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(LookupError, PermissionError):
                os.killpg(pid, signal.SIGKILL)
            with contextlib.suppress(subprocess.TimeoutExpired):
                job.process.wait(timeout=1)
        
        remove_job(pid)
        return f"Job {pid} created by {job.bash_command} stopped successfully."


def read_log_tail(log_path: Path, *, max_chars: int=4000)->str:
    """Returns the last `max_chars` bytes of a log file, or the whole file if smaller."""

    if not log_path.exists():
        return ""

    # Reading the log file
    text=log_path.read_text(encoding="utf-8", errors="replace")

    # If log file is larger than max_chars, return the last max_chars bytes
    if len(text)>max_chars:
        return text[-max_chars:]
    
    return text
