from google.adk.agents import Agent
from google.adk.tools import agent_tool
from typing import Dict, Any
import os
import logging
from contextlib import asynccontextmanager
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams
from shell_utils import shell_command

logger = logging.getLogger(__name__)

def get_model() -> str:
    """Get model from environment with consistent default."""
    return os.environ.get('MODEL', 'gemini-2.5-flash')

# Create MCP tools using async context manager decorator
@asynccontextmanager
async def mcp_connection():
    """Async context manager for MCP toolset lifecycle."""
    # Log environment configuration
    jira_url = os.environ.get('JIRA_URL', 'Not set')
    mcp_server_url = os.environ.get('MCP_JIRA_URL', 'http://mcp-atlassian:9000/sse')

    logger.info(f"JIRA Server: {jira_url}")
    logger.info(f"MCP Server: {mcp_server_url}")

    toolset = None
    try:
        connection_params = SseServerParams(url=mcp_server_url)
        toolset = MCPToolset(connection_params=connection_params)

        logger.info("MCP connection established")
        yield [toolset]

    except Exception as e:
        logger.error(f"MCP connection failed: {e}")
        yield []
    finally:
        # Cleanup happens here automatically
        if toolset:
            try:
                await toolset.close()
                logger.info("MCP connection closed")
            except Exception as e:
                logger.warning(f"MCP cleanup error: {e}")


def get_config() -> Dict[str, Any]:
    """Get configuration for the issue analyzer agent."""
    return {
        'jira_issue': os.environ.get('JIRA_ISSUE', 'RHEL-78418'),
        'model': get_model(),
    }

def create_issue_analyzer_prompt(config: Dict[str, Any]) -> str:
    """Creates the prompt for the JIRA issue analyzer agent."""

    jira_issue = config['jira_issue']

    return f"""You are an AI Agent tasked to analyze Jira issues.

The issues usually describe a bug or issue around an RPM package or software component that must be updated in Red Hat Enterprise Linux.
Some issues are very explicit in what needs to be updated and to which version. Others are more vague.
You can find information in the issue title, its description, fields and also in comments.
Make sure to take a close look before reporting the data.

IMPORTANT GUIDELINES:
- **Tool Usage**: You have shell_command (for executing commands) and JiraAgent (for JIRA operations) - use them directly!
- **Command Execution Rules**:
  - Use shell_command tool for ALL command execution
  - If a command shows "no output" or empty STDOUT, that is a VALID result - do not retry
  - Commands that succeed with no output are normal - report success
- **Never create, delete, update or modify an Issue in Jira**

Follow the following steps:

1. Retrieve the Jira issue (ALL the fields) using JiraAgent with jira_get_issue tool for issue key: {jira_issue}

2. Identify the name of the package that must be updated. Let's refer to it as `<package_name>`.
    * Confirm the `<package_name>` repository exists by using shell_command tool to run: `git ls-remote https://gitlab.com/redhat/centos-stream/rpms/<package_name>`.
    * A successful command (exit code 0) confirms its existence.
    * If the `<package_name>` does not exist, take another look at the Jira issue. You may have picked the wrong package or name.

3. Identify the `<package_version>` the `<package_name>` should be updated or rebased to.

4. Identify the target RHEL version and from that the target branch `<git_branch>` of the `<package_name>` on GitLab to update.
    * The RHEL version is usually set in the version related fields of the Jira issue (e.g. fix_versions, examine all the fields).
    * A RHEL version named rhel-N maps to a branch named cNs.
    * Verify the branch exists on GitLab using shell_command tool.

Output the following:
PACKAGE_NAME: [package name]
PACKAGE_VERSION: [target version]
GIT_BRANCH: [target branch]
"""



def create_issue_analyzer_agent(mcp_tools=None):
    """Factory function to create issue analyzer agent."""
    config = get_config()
    model = config['model']

    # Build tools list - use shell_command directly
    tools = [shell_command]

    # Add MCP tools if provided (for JIRA operations)
    if mcp_tools:
        jira_agent = Agent(
            model=model,
            name='JiraAgent',
            instruction='You are a specialist in JIRA operations. Use JIRA tools to fetch and analyze issues.',
            tools=mcp_tools,
        )
        tools.append(agent_tool.AgentTool(agent=jira_agent))

    return Agent(
        name="issue_analyzer",
        model=model,
        description="Analyzes JIRA issues to extract package update requirements",
        instruction=create_issue_analyzer_prompt(config),
        tools=tools,
        output_key="issue_analysis_result",
    )
