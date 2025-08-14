import asyncio
from typing import Any

from pydantic import BaseModel, Field

from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.tools import JSONToolOutput, Tool, ToolRunOptions

from utils import run_subprocess


class RunShellCommandToolInput(BaseModel):
    command: str = Field(description="Command to run")


class RunShellCommandToolResult(BaseModel):
    exit_code: int
    stdout: str | None
    stderr: str | None


class RunShellCommandToolOutput(JSONToolOutput[RunShellCommandToolResult]):
    pass


class RunShellCommandTool(Tool[RunShellCommandToolInput, ToolRunOptions, RunShellCommandToolOutput]):
    name = "run_shell_command"
    description = """
        Runs the specified command in a shell. Returns a dictionary with exit code
        and captured stdout and stderr.
    """
    input_schema = RunShellCommandToolInput

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(
            namespace=["tool", "commands", self.name],
            creator=self,
        )

    async def _run(
        self, tool_input: RunShellCommandToolInput, options: ToolRunOptions | None, context: RunContext
    ) -> RunShellCommandToolOutput:
        exit_code, stdout, stderr = await run_subprocess(tool_input.command, shell=True)
        result = {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
        }
        return RunShellCommandToolOutput(RunShellCommandToolResult.model_validate(result))
