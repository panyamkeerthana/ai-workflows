import os
import subprocess
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from ogr.factory import get_project
from pydantic import Field


def fork_repository(
    repository: Annotated[str, Field(description="Repository URL")],
) -> str:
    """
    Creates a new fork of the specified repository if it doesn't exist yet,
    otherwise gets the existing fork. Returns a clonable git URL of the fork
    or an error message on failure.
    """
    # TODO: add support for destination namespace
    project = get_project(url=repository, token=os.getenv("GITLAB_TOKEN"))
    if not project:
        return "Failed to get the specified repository"
    fork = project.get_fork(create=True)
    if not fork:
        return "Failed to fork the specified repository"
    return fork.get_git_urls()["git"]


def open_merge_request(
    fork_url: Annotated[str, Field(description="URL of the fork to open the MR from")],
    title: Annotated[str, Field(description="MR title")],
    description: Annotated[str, Field(description="MR description")],
    target: Annotated[str, Field(description="Target branch (in the original repository)")],
    source: Annotated[str, Field(description="Source branch (in the fork)")],
) -> str:
    """
    Opens a new merge request from the specified fork against its original repository.
    Returns URL of the opened merge request or an error message on failure.
    """
    project = get_project(url=fork_url, token=os.getenv("GITLAB_TOKEN"))
    if not project:
        return "Failed to get the specified fork"
    pr = project.create_pr(title, description, target, source)
    if not pr:
        return "Failed to open the merge request"
    return pr.url


def push_to_remote_repository(
    repository: Annotated[str, Field(description="Repository URL")],
    clone_path: Annotated[Path, Field(description="Absolute path to local clone of the repository")],
    branch: Annotated[str, Field(description="Branch to push")],
    force: Annotated[bool, Field(description="Whether to overwrite the remote ref")] = False,
) -> str:
    """
    Pushes the specified branch from a local clone to the specified remote repository.
    """
    url = urlparse(repository)
    token = os.getenv("GITLAB_TOKEN")
    remote = url._replace(netloc=f"oauth2:{token}@{url.hostname}").geturl()
    command = ["git", "push", remote, branch]
    if force:
        command.append("--force")
    if subprocess.run(command, cwd=clone_path).returncode != 0:
        return "Failed to push to the specified repository"
    return f"Successfully pushed the specified branch to {repository}"
