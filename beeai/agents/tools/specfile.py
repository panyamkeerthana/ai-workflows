import asyncio
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from specfile import Specfile

from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.tools import StringToolOutput, Tool, ToolRunOptions


# version update & release reset ?
# patch addition ?


class AddChangelogEntryToolInput(BaseModel):
    spec: Path = Field(description="Absolute path to a spec file")
    content: list[str] = Field(
        description="""
        Content of the entry as a list of lines, maximum line length should be 80 characters,
        every paragraph should start with "- "
        """
    )
    author: str = Field(description="Author of the entry (change)")
    email: str = Field(description="E-mail address of the author")


class AddChangelogEntryTool(Tool[AddChangelogEntryToolInput, ToolRunOptions, StringToolOutput]):
    name = "add_changelog_entry"
    description = """
    Adds a new changelog entry to the specified spec file. Returns error message on failure.
    """
    input_schema = AddChangelogEntryToolInput

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(
            namespace=["tool", "specfile", self.name],
            creator=self,
        )

    async def _run(
        self, tool_input: AddChangelogEntryToolInput, options: ToolRunOptions | None, context: RunContext
    ) -> StringToolOutput:
        try:
            with Specfile(tool_input.spec) as spec:
                spec.add_changelog_entry(tool_input.content, author=tool_input.author, email=tool_input.email)
        except Exception as e:
            return StringToolOutput(result=f"Failed to add changelog entry: {e}")
        return StringToolOutput()


class BumpReleaseToolInput(BaseModel):
    spec: Path = Field(description="Absolute path to a spec file")


class BumpReleaseTool(Tool[BumpReleaseToolInput, ToolRunOptions, StringToolOutput]):
    name = "bump_release"
    description = """
    Bumps (increments) the value of `Release` in the specified spec file.
    Returns error message on failure.
    """
    input_schema = BumpReleaseToolInput

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(
            namespace=["tool", "specfile", self.name],
            creator=self,
        )

    async def _run(
        self, tool_input: BumpReleaseToolInput, options: ToolRunOptions | None, context: RunContext
    ) -> StringToolOutput:
        try:
            with Specfile(tool_input.spec) as spec:
                spec.bump_release()
        except Exception as e:
            return StringToolOutput(result=f"Failed to bump release: {e}")
        return StringToolOutput()
