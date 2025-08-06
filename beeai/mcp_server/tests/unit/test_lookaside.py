import subprocess
from pathlib import Path

import pytest
from flexmock import flexmock

import lookaside_tools
from lookaside_tools import download_sources, upload_sources


@pytest.mark.parametrize(
    "internal", [False, True],
)
def test_download_sources(internal):
    def run(cmd, **kwargs):
        assert cmd == ["rhpkg" if internal else "centpkg", "sources"]
        return flexmock(returncode=0)

    flexmock(subprocess).should_receive("run").replace_with(run)
    result =  download_sources(dist_git_path=".", internal=internal)
    assert result.startswith("Successfully")


@pytest.mark.parametrize(
    "internal", [False, True],
)
def test_upload_sources(internal):
    new_sources = ["package-1.2-3.tar.gz"]

    def run(cmd, **kwargs):
        assert cmd == ["rhpkg" if internal else "centpkg", "new-sources", *new_sources]
        return flexmock(returncode=0)

    flexmock(lookaside_tools).should_receive("init_kerberos_ticket").and_return(True).once()
    flexmock(subprocess).should_receive("run").replace_with(run)
    result =  upload_sources(dist_git_path=".", new_sources=new_sources, internal=internal)
    assert result.startswith("Successfully")
