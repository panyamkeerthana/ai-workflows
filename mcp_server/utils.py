import asyncio
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


REPO_CLEANUP_DAYS = 14


async def extract_principal(keytab_file: str) -> str | None:
    """
    Extracts principal from the specified keytab file. Assumes that there is
    a single principal in the keytab.

    Args:
        keytab_file: Path to a keytab file.

    Returns:
        Extracted principal.
    """
    proc = await asyncio.create_subprocess_exec(
        "klist", "-k", "-K", "-e", keytab_file,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    print(stdout.decode(), flush=True)
    if proc.returncode:
        print(stderr.decode(), flush=True)
        return None
    key_pattern = re.compile(r"^\s*(\d+)\s+(\S+)\s+\((\S+)\)\s+\((\S+)\)$")
    for line in stdout.decode().splitlines():
        if not (match := key_pattern.match(line)):
            continue
        # just return the principal associated with the first key
        return match.group(2)
    return None


async def init_kerberos_ticket() -> str | None:
    """
    Initializes Kerberos ticket unless it's already present in a credentials cache.
    On success, returns the associated principal.
    """
    keytab_file = os.getenv("KEYTAB_FILE")
    principal = await extract_principal(keytab_file)
    if not principal:
        print("Failed to extract principal", flush=True)
        return None
    proc = await asyncio.create_subprocess_exec(
        "klist", "-l",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    print(stdout.decode(), flush=True)
    if proc.returncode:
        print(stderr.decode(), flush=True)
    elif any(l for l in stdout.decode().splitlines() if principal in l and "Expired" not in l):
        return principal
    env = os.environ.copy()
    env.update({"KRB5_TRACE": "/dev/stdout"})
    proc = await asyncio.create_subprocess_exec("kinit", "-k", "-t", keytab_file, principal, env=env)
    return None if await proc.wait() else principal

def cleanup_stale_directories(git_repos_path: Path, cutoff_time: datetime) -> int:
    """
    Finds and deletes stale directories in the specified path.
    Ignores all exceptions that could occur during cleanup.
    Return the number of deleted directories.
    """
    deleted_count = 0
    for item_path in git_repos_path.iterdir():
        try:
            if not item_path.is_dir() or not item_path.name.lower().startswith("rhel-"):
                continue

            mod_time = datetime.fromtimestamp(item_path.stat().st_mtime)
            if mod_time < cutoff_time:
                logger.info(f"Deleting old directory: {item_path}")
                shutil.rmtree(item_path, ignore_errors=True)
                deleted_count += 1
        except Exception as ex:
            logger.warning(f"Failed to delete directory {item_path}: {ex}")
            continue

    return deleted_count

async def clean_stale_repositories() -> int:
    """
    Cleans up stale repositories (older than 14 days).

    Don't raise an error if the cleanup fails.
    Return the number of deleted directories.
    """
    git_repos_path_str = os.environ["GIT_REPO_BASEPATH"]

    logger.info(f"Cleaning directories in {git_repos_path_str} older than {REPO_CLEANUP_DAYS} days")

    git_repos_path = Path(git_repos_path_str)
    if not git_repos_path.is_dir():
        logger.info(f"Git repos path {git_repos_path_str} is not a directory. Skipping cleanup.")
        return 0

    cutoff_time = datetime.now() - timedelta(days=REPO_CLEANUP_DAYS)

    deleted_count = await asyncio.to_thread(cleanup_stale_directories, git_repos_path, cutoff_time)
    logger.info(f"Repository cleanup completed successfully. Deleted {deleted_count} directories.")
    return deleted_count
