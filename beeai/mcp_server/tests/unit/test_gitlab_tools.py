import subprocess
from pathlib import Path

from flexmock import flexmock
from ogr.services.gitlab import GitlabService

from gitlab_tools import fork_repository, open_merge_request, push_to_remote_repository


def test_fork_repository():
    repository = "https://gitlab.com/redhat/centos-stream/rpms/bash"
    clone_url = "https://gitlab.com/ai-bot/bash.git"
    flexmock(GitlabService).should_receive("get_project_from_url").with_args(
        url=repository
    ).and_return(
        flexmock(get_fork=lambda create: flexmock(get_git_urls=lambda: {"git": clone_url}))
    )
    assert fork_repository(repository=repository) == clone_url


def test_open_merge_request():
    fork_url = "https://gitlab.com/ai-bot/bash.git"
    title = "Fix RHEL-12345"
    description = "Resolves RHEL-12345"
    target = "c10s"
    source = "automated-package-update-RHEL-12345"
    mr_url = "https://gitlab.com/redhat/centos-stream/rpms/bash/-/merge_requests/1"
    pr_mock = flexmock(url=mr_url)
    flexmock(GitlabService).should_receive("get_project_from_url").with_args(
        url=fork_url
    ).and_return(flexmock(create_pr=lambda title, body, target, source: pr_mock))
    pr_mock.should_receive("add_label").with_args("jotnar_needs_attention").once()
    assert (
        open_merge_request(
            fork_url=fork_url,
            title=title,
            description=description,
            target=target,
            source=source,
        )
        == mr_url
    )


def test_push_to_remote_repository():
    repository = "https://gitlab.com/ai-bot/bash.git"
    branch = "automated-package-update-RHEL-12345"
    clone_path = Path("/git-repos/bash")

    def run(cmd, **kwargs):
        assert cmd[0:2] == ["git", "push"]
        assert cmd[2].endswith(repository.removeprefix("https://"))
        assert cmd[3] == branch
        assert kwargs.get("cwd") == clone_path
        return flexmock(returncode=0)

    flexmock(subprocess).should_receive("run").replace_with(run)
    result = push_to_remote_repository(repository=repository, clone_path=clone_path, branch=branch)
    assert result.startswith("Successfully")
