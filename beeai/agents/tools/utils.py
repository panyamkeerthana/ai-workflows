import asyncio
from pathlib import Path
from typing import Callable, Optional, Union


async def run_command(
    cmd: Union[list[str], str],
    cwd: Optional[Path] = None,
    subprocess_function: Callable = asyncio.create_subprocess_exec
) -> dict[str, str | int]:
    """
    Run a shell command asynchronously and capture its output.

    Args:
        cmd: The command to run. Can be a list of arguments (for exec) or a string (for shell).
        cwd: Optional working directory to run the command in.
        subprocess_function: The asyncio subprocess function to use (e.g., create_subprocess_exec or create_subprocess_shell).

    Returns:
        A dictionary with:
            - "exit_code": The process exit code (int)
            - "stdout": The standard output as a string, or None
            - "stderr": The standard error as a string, or None
    """
    if subprocess_function is asyncio.create_subprocess_exec:
        proc = await subprocess_function(
            cmd[0],
            *cmd[1:],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
    else:
        proc = await subprocess_function(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

    stdout, stderr = await proc.communicate()

    return {
        "exit_code": proc.returncode,
        "stdout": stdout.decode() if stdout else None,
        "stderr": stderr.decode() if stderr else None,
    }
