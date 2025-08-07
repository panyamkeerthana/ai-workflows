import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.tools import JSONToolOutput, Tool, ToolRunOptions


class GitPatchCreationToolInput(BaseModel):
    repository_path: Path = Field(description="Absolute path to the git repository")
    patch_file_path: Path = Field(description="Absolute path where the patch file should be saved")


class GitPatchCreationToolResult(BaseModel):
    success: bool = Field(description="Whether the patch creation was successful")
    patch_file_path: str = Field(description="Path to the created patch file")
    error: str | None = Field(description="Error message if patch creation failed", default=None)


class GitPatchCreationToolOutput(JSONToolOutput[GitPatchCreationToolResult]):
    """ Returns a dictionary with success or error and the path to the created patch file. """


async def run_command(cmd: list[str], cwd: Path) -> dict[str, str | int]:
    proc = await asyncio.create_subprocess_exec(
        cmd[0],
        *cmd[1:],
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )

    stdout, stderr = await proc.communicate()

    return {
        "exit_code": proc.returncode,
        "stdout": stdout.decode() if stdout else None,
        "stderr": stderr.decode() if stderr else None,
    }

class GitPatchCreationTool(Tool[GitPatchCreationToolInput, ToolRunOptions, GitPatchCreationToolOutput]):
    name = "git_patch_create"
    description = """
    Creates a patch file from the specified git repository with an active git-am session
    and after you resolved all merge conflicts. The tool generates a patch file that can be
    applied later in the RPM build process. Returns a dictionary with success or error and
    the path to the created patch file.
    """
    input_schema = GitPatchCreationToolInput

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(
            namespace=["tool", "git", self.name],
            creator=self,
        )

    async def _run(
        self, tool_input: GitPatchCreationToolInput, options: ToolRunOptions | None, context: RunContext
    ) -> GitPatchCreationToolOutput:
        # Ensure the repository path exists and is a git repository
        if not tool_input.repository_path.exists():
            return GitPatchCreationToolOutput(
                result=GitPatchCreationToolResult(
                    success=False,
                    patch_file_path="",
                    patch_content="",
                    error=f"Repository path does not exist: {tool_input.repository_path}"
                )
            )

        git_dir = tool_input.repository_path / ".git"
        if not git_dir.exists():
            return GitPatchCreationToolOutput(
                result=GitPatchCreationToolResult(
                    success=False,
                    patch_file_path="",
                    patch_content="",
                    error=f"Not a git repository: {tool_input.repository_path}"
                )
            )

        # list all untracked files in the repository
        cmd = ["git", "ls-files", "--others", "--exclude-standard"]
        result = await run_command(cmd, cwd=tool_input.repository_path)
        if result["exit_code"] != 0:
            return GitPatchCreationToolOutput(
                result=GitPatchCreationToolResult(
                    success=False,
                    patch_file_path="",
                    patch_content="",
                    error=f"Git command failed: {result['stderr']}"
                )
            )
        untracked_files = result["stdout"].splitlines()
        # list staged as well since that's what the agent usually does after it resolves conflicts
        cmd = ["git", "diff", "--name-only", "--cached"]
        result = await run_command(cmd, cwd=tool_input.repository_path)
        if result["exit_code"] != 0:
            return GitPatchCreationToolOutput(
                result=GitPatchCreationToolResult(
                    success=False,
                    patch_file_path="",
                    patch_content="",
                    error=f"Git command failed: {result['stderr']}"
                )
            )
        staged_files = result["stdout"].splitlines()
        all_files = untracked_files + staged_files
        # make sure there are no *.rej files in the repository
        rej_files = [file for file in all_files if file.endswith(".rej")]
        if rej_files:
            return GitPatchCreationToolOutput(
                result=GitPatchCreationToolResult(
                    success=False,
                    patch_file_path="",
                    patch_content="",
                    error="Merge conflicts detected in the repository: "
                    f"{tool_input.repository_path}, {rej_files}"
                )
            )

        # git-am leaves the repository in a dirty state, so we need to stage everything
        # I considered to inspect the patch and only stage the files that are changed by the patch,
        # but the backport process could create new files or change new ones
        # so let's go the naive route: git add -A
        cmd = ["git", "add", "-A"]
        result = await run_command(cmd, cwd=tool_input.repository_path)
        if result["exit_code"] != 0:
            return GitPatchCreationToolOutput(
                result=GitPatchCreationToolResult(
                    success=False,
                    patch_file_path="",
                    patch_content="",
                    error=f"Git command failed: {result['stderr']}"
                )
            )
        # continue git-am process
        cmd = ["git", "am", "--continue"]
        result = await run_command(cmd, cwd=tool_input.repository_path)
        if result["exit_code"] != 0:
            return GitPatchCreationToolOutput(
                result=GitPatchCreationToolResult(
                    success=False,
                    patch_file_path="",
                    patch_content="",
                    error=f"git-am failed: {result['stderr']}, out={result['stdout']}"
                )
            )
        # good, now we should have the patch committed, so let's get the file
        cmd = [
            "git", "format-patch",
            "--output",
            str(tool_input.patch_file_path),
            "HEAD~1..HEAD"
        ]
        result = await run_command(cmd, cwd=tool_input.repository_path)
        if result["exit_code"] != 0:
            return GitPatchCreationToolOutput(
                result=GitPatchCreationToolResult(
                    success=False,
                    patch_file_path="",
                    patch_content="",
                    error=f"git-format-patch failed: {result['stderr']}"
                )
            )
        return GitPatchCreationToolOutput(
            result=GitPatchCreationToolResult(
                success=True,
                patch_file_path=str(tool_input.patch_file_path),
                error=None
            )
        )