import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.tools import StringToolOutput, Tool, ToolRunOptions


class GitPatchCreationToolInput(BaseModel):
    repository_path: str = Field(description="Absolute path to the git repository")
    patch_file_path: str = Field(description="Absolute path where the patch file should be saved")


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

class GitPatchCreationTool(Tool[GitPatchCreationToolInput, ToolRunOptions, StringToolOutput]):
    name = "git_patch_create"
    description = """
    Creates a patch file from the specified git repository with an active git-am session.
    The tool expects you resolved all conflicts. It generates a patch file that can be
    applied later in the RPM build process.
    """
    input_schema = GitPatchCreationToolInput

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(
            namespace=["tool", "git", self.name],
            creator=self,
        )

    async def _run(
        self, tool_input: GitPatchCreationToolInput, options: ToolRunOptions | None, context: RunContext
    ) -> StringToolOutput:
        try:
            # Ensure the repository path exists and is a git repository
            tool_input_path = Path(tool_input.repository_path)
            if not tool_input_path.exists():
                return StringToolOutput(result=f"ERROR: Repository path does not exist: {tool_input_path}")

            git_dir = tool_input_path / ".git"
            if not git_dir.exists():
                return StringToolOutput(result=f"ERROR: Not a git repository: {tool_input_path}")

            # list all untracked files in the repository
            rej_candidates = []
            cmd = ["git", "ls-files", "--others", "--exclude-standard"]
            result = await run_command(cmd, cwd=tool_input_path)
            if result["exit_code"] != 0:
                return StringToolOutput(result=f"ERROR: Git command failed: {result['stderr']}")
            if result["stdout"]:  # none means no untracked files
                rej_candidates.extend(result["stdout"].splitlines())
            # list staged as well since that's what the agent usually does after it resolves conflicts
            cmd = ["git", "diff", "--name-only", "--cached"]
            result = await run_command(cmd, cwd=tool_input_path)
            if result["exit_code"] != 0:
                return StringToolOutput(result=f"ERROR: Git command failed: {result['stderr']}")
            if result["stdout"]:
                rej_candidates.extend(result["stdout"].splitlines())
            if rej_candidates:
                # make sure there are no *.rej files in the repository
                rej_files = [file for file in rej_candidates if file.endswith(".rej")]
                if rej_files:
                    return StringToolOutput(result=f"ERROR: Merge conflicts detected in the repository: "
                                            f"{tool_input.repository_path}, {rej_files}")

            # git-am leaves the repository in a dirty state, so we need to stage everything
            # I considered to inspect the patch and only stage the files that are changed by the patch,
            # but the backport process could create new files or change new ones
            # so let's go the naive route: git add -A
            cmd = ["git", "add", "-A"]
            result = await run_command(cmd, cwd=tool_input_path)
            if result["exit_code"] != 0:
                return StringToolOutput(result=f"ERROR: Git command failed: {result['stderr']}")
            # continue git-am process
            cmd = ["git", "am", "--continue"]
            result = await run_command(cmd, cwd=tool_input_path)
            if result["exit_code"] != 0:
                return StringToolOutput(result=f"ERROR: git-am failed: {result['stderr']},"
                f" out={result['stdout']}")
            # good, now we should have the patch committed, so let's get the file
            cmd = [
                "git", "format-patch",
                "--output",
                tool_input.patch_file_path,
                "HEAD~1..HEAD"
            ]
            result = await run_command(cmd, cwd=tool_input_path)
            if result["exit_code"] != 0:
                return StringToolOutput(result=f"ERROR: git-format-patch failed: {result['stderr']}")
            return StringToolOutput(result=f"Successfully created a patch file: {tool_input.patch_file_path}")
        except Exception as e:
            # we absolutely need to do this otherwise the error won't appear anywhere
            return StringToolOutput(result=f"ERROR: {e}")