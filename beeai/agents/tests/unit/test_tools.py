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
    SetZStreamReleaseTool,
    SetZStreamReleaseToolInput,
)
from tools.text import (
    CreateTool,
    CreateToolInput,
    ViewTool,
    ViewToolInput,
    InsertTool,
    InsertToolInput,
    StrReplaceTool,
    StrReplaceToolInput,
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


@pytest.fixture
def autorelease_spec(tmp_path):
    spec = tmp_path / "test.spec"
    spec.write_text(
        dedent(
            """
            Name:           test
            Version:        0.1
            Release:        %autorelease
            Summary:        Test package

            License:        MIT

            %description
            Test package

            %changelog
            %autochangelog
            """
        )
    )
    return spec


@pytest.mark.asyncio
async def test_set_zstream_release(autorelease_spec):
    latest_ystream_evr = "0.1-4.el10"
    tool = SetZStreamReleaseTool()
    output = await tool.run(
        input=SetZStreamReleaseToolInput(spec=autorelease_spec, latest_ystream_evr=latest_ystream_evr)
    ).middleware(GlobalTrajectoryMiddleware(pretty=True))
    result = output.result
    assert not result
    assert autorelease_spec.read_text().splitlines()[3] == "Release:        4%{?dist}.%{autorelease -n}"


@pytest.mark.asyncio
async def test_create(tmp_path):
    test_file = tmp_path / "test.txt"
    content = "Line 1\nLine 2\n"
    tool = CreateTool()
    output = await tool.run(input=CreateToolInput(file=test_file, content=content)).middleware(
        GlobalTrajectoryMiddleware(pretty=True)
    )
    result = output.result
    assert not result
    assert test_file.read_text() == content


@pytest.mark.asyncio
async def test_view(tmp_path):
    test_dir = tmp_path
    test_file = test_dir / "test.txt"
    content = "Line 1\nLine 2\nLine 3\n"
    test_file.write_text(content)
    tool = ViewTool()
    output = await tool.run(input=ViewToolInput(path=test_dir)).middleware(
        GlobalTrajectoryMiddleware(pretty=True)
    )
    result = output.result
    assert result == "test.txt\n"
    output = await tool.run(input=ViewToolInput(path=test_file)).middleware(
        GlobalTrajectoryMiddleware(pretty=True)
    )
    result = output.result
    assert result == content
    output = await tool.run(input=ViewToolInput(path=test_file, view_range=(2, -1))).middleware(
        GlobalTrajectoryMiddleware(pretty=True)
    )
    result = output.result
    assert (
        result
        == dedent(
            """
            Line 2
            Line 3
            """
        )[1:]
    )
    output = await tool.run(input=ViewToolInput(path=test_file, view_range=(1, 2))).middleware(
        GlobalTrajectoryMiddleware(pretty=True)
    )
    result = output.result
    assert (
        result
        == dedent(
            """
            Line 1
            Line 2
            """
        )[1:]
    )


@pytest.mark.parametrize(
    "line, content",
    [
        (
            0,
            dedent(
                """
                Inserted line
                Line 1
                Line 2
                Line 3
                """
            )[1:],
        ),
        (
            1,
            dedent(
                """
                Line 1
                Inserted line
                Line 2
                Line 3
                """
            )[1:],
        ),
    ],
)
@pytest.mark.asyncio
async def test_insert(line, content, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3\n")
    tool = InsertTool()
    output = await tool.run(
        input=InsertToolInput(file=test_file, line=line, new_string="Inserted line")
    ).middleware(GlobalTrajectoryMiddleware(pretty=True))
    result = output.result
    assert not result
    assert test_file.read_text() == content


@pytest.mark.asyncio
async def test_str_replace(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3\n")
    tool = StrReplaceTool()
    output = await tool.run(
        input=StrReplaceToolInput(file=test_file, old_string="Line 2", new_string="LINE_2")
    ).middleware(GlobalTrajectoryMiddleware(pretty=True))
    result = output.result
    assert not result
    assert (
        test_file.read_text()
        == dedent(
            """
            Line 1
            LINE_2
            Line 3
            """
        )[1:]
    )
