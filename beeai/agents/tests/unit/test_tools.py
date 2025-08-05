import datetime
from textwrap import dedent

import pytest
from flexmock import flexmock
from specfile import specfile

from beeai_framework.middleware.trajectory import GlobalTrajectoryMiddleware

from tools.commands import RunShellCommandTool, RunShellCommandToolInput
from tools.specfile import (
    AddChangelogEntryTool,
    AddChangelogEntryToolInput,
    BumpReleaseTool,
    BumpReleaseToolInput,
)


@pytest.mark.parametrize(
    "command, exit_code, stdout, stderr",
    [
        (
            "exit 28",
            28,
            None,
            None,
        ),
        (
            "echo -n test",
            0,
            "test",
            None,
        ),
        (
            "echo -n error >&2 && false",
            1,
            None,
            "error",
        ),
    ],
)
@pytest.mark.asyncio
async def test_run_shell_command(command, exit_code, stdout, stderr):
    tool = RunShellCommandTool()
    output = await tool.run(input=RunShellCommandToolInput(command=command)).middleware(
        GlobalTrajectoryMiddleware(pretty=True)
    )
    result = output.to_json_safe()
    assert result.exit_code == exit_code
    assert result.stdout == stdout
    assert result.stderr == stderr


@pytest.fixture
def minimal_spec(tmp_path):
    spec = tmp_path / "test.spec"
    spec.write_text(
        dedent(
            """
            Name:           test
            Version:        0.1
            Release:        2%{?dist}
            Summary:        Test package

            License:        MIT

            %description
            Test package

            %changelog
            * Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 0.1-1
            - first version
            """
        )
    )
    return spec


@pytest.mark.asyncio
async def test_add_changelog_entry(minimal_spec):
    content = ["- some change", "  second line"]
    author = "rhel-packaging-agent"
    email = "rhel-packaging-agent@redhat.com"
    flexmock(specfile).should_receive("datetime").and_return(
        flexmock(
            datetime=flexmock(now=lambda _: flexmock(date=lambda: datetime.date(2025, 8, 5))),
            timezone=flexmock(utc=None),
        )
    )
    tool = AddChangelogEntryTool()
    output = await tool.run(
        input=AddChangelogEntryToolInput(spec=minimal_spec, content=content, author=author, email=email)
    ).middleware(GlobalTrajectoryMiddleware(pretty=True))
    result = output.result
    assert not result
    assert minimal_spec.read_text().splitlines()[-7:-2] == [
        "%changelog",
        "* Tue Aug 05 2025 rhel-packaging-agent <rhel-packaging-agent@redhat.com> - 0.1-2",
        "- some change",
        "  second line",
        "",
    ]


@pytest.mark.asyncio
async def test_bump_release(minimal_spec):
    tool = BumpReleaseTool()
    output = await tool.run(input=BumpReleaseToolInput(spec=minimal_spec)).middleware(
        GlobalTrajectoryMiddleware(pretty=True)
    )
    result = output.result
    assert not result
    assert minimal_spec.read_text().splitlines()[3] == "Release:        3%{?dist}"
