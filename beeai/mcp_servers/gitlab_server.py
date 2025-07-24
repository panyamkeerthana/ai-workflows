import os
from typing import Annotated

from fastmcp import FastMCP
from ogr.factory import get_project
from pydantic import Field


mcp = FastMCP(name="GitLab")


@mcp.tool
def fork_repository(
    repository: Annotated[str, Field(description="Repository URL")],
) -> str | None:
    """
    Creates a new fork of the specified repository if it doesn't exist yet,
    otherwise gets the existing fork. Returns a clonable git URL of the fork.
    """
    # TODO: add support for destination namespace
    project = get_project(url=repository, token=os.getenv("GITLAB_TOKEN"))
    if not project:
        return None
    fork = project.get_fork(create=True)
    if not fork:
        return None
    return fork.get_git_urls()["git"]


@mcp.tool
def open_merge_request(
    fork_url: Annotated[str, Field(description="URL of the fork to open the MR from")],
    title: Annotated[str, Field(description="MR title")],
    description: Annotated[str, Field(description="MR description")],
    target: Annotated[str, Field(description="Target branch (in the original repository)")],
    source: Annotated[str, Field(description="Source branch (in the fork)")],
) -> str | None:
    """
    Opens a new merge request against the specified repository. Returns URL
    of the opened merge request.
    """
    project = get_project(url=fork_url, token=os.getenv("GITLAB_TOKEN"))
    if not project:
        return None
    pr = project.create_pr(title, description, target, source)
    if not pr:
        return None
    return pr.url


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=os.getenv("SSE_PORT"))
