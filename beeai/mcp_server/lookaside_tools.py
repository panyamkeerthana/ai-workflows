import subprocess
from pathlib import Path
from typing import Annotated

from pydantic import Field

from utils import init_kerberos_ticket


def download_sources(
    dist_git_path: Annotated[Path, Field(description="Path to cloned dist-git repository")],
    internal: Annotated[bool, Field(description="Whether to use internal RHEL dist-git instead of CentOS Stream one")] = False,
) -> str:
    """
    Downloads sources from lookaside cache.
    """
    tool = "rhpkg" if internal else "centpkg"
    if subprocess.run([tool, "sources"], cwd=dist_git_path).returncode != 0:
        return "Failed to download sources"
    return "Successfully downloaded sources from lookaside cache"


def upload_sources(
    dist_git_path: Annotated[Path, Field(description="Path to cloned dist-git repository")],
    new_sources: Annotated[list[str], Field(description="List of new sources (file names) to upload")],
    internal: Annotated[bool, Field(description="Whether to use internal RHEL dist-git instead of CentOS Stream one")] = False,
) -> str:
    """
    Uploads the specified sources to lookaside cache. Also updates the `sources` and `.gitignore` files
    accordingly and adds them to git index.
    """
    tool = "rhpkg" if internal else "centpkg"
    if not init_kerberos_ticket():
        return "Failed to initialize Kerberos ticket"
    if subprocess.run([tool, "new-sources", *new_sources], cwd=dist_git_path).returncode != 0:
        return "Failed to upload sources"
    return "Successfully uploaded the specified new sources to lookaside cache"
