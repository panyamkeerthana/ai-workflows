from google.adk.agents import Agent
from google.adk.tools import agent_tool, google_search
from google.adk.code_executors import BuiltInCodeExecutor
from typing import Dict, Any
import os

def get_model() -> str:
    """Get model from environment with consistent default."""
    return os.environ.get('MODEL', 'gemini-2.5-flash')

def get_config() -> Dict[str, Any]:
    """Get configuration for the combined version checker and package updater agent."""
    return {
        'package': os.environ.get('PACKAGE', ''),
        'version': os.environ.get('VERSION', ''),
        'jira_issue': os.environ.get('JIRA_ISSUE', ''),
        'git_url': os.environ.get('GIT_URL', 'https://gitlab.com/redhat/centos-stream/rpms'),
        'dist_git_branch': os.environ.get('DIST_GIT_BRANCH', 'c10s'),
        'git_user': os.environ.get('GIT_USER', 'RHEL Packaging Agent'),
        'git_email': os.environ.get('GIT_EMAIL', 'rhel-packaging-agent@redhat.com'),
        'gitlab_user': os.environ.get('GITLAB_USER',''),
        'model': get_model(),
    }

def create_package_updater_prompt(config: Dict[str, Any]) -> str:
    """Creates the prompt for the combined version checker and package updater agent."""

    return f"""**Context**
You are a CentOS package version checker and updater agent. You first check if a package needs updating, then perform the actual package update if required.

**IMPORTANT GUIDELINES**
- **Tool Usage**: You have CodeAgent (shell commands) and SearchAgent (web search) - USE THEM!
- **No Placeholders**: Execute actual commands and provide real results
- **Context Tracking**: Remember directories, files, and commands from previous steps
- **Error Handling**: Show actual error messages, don't give up on first failure
- **CRITICAL: Working Directory Management**:
  - CodeAgent does NOT maintain working directory between calls
  - ALWAYS use `cd /path && command` format to ensure you're in the right directory
  - Example: `cd /tmp/package-update-work/[PACKAGE_NAME] && pwd && ls -la`
  - NEVER assume you're still in a directory from a previous CodeAgent call
- **Configuration**:
  - Package repository: {config['git_url']}/[package_name]
  - Git branch: {config['dist_git_branch']}
  - Available config: PACKAGE="{config['package']}", VERSION="{config['version']}", JIRA_ISSUE="{config['jira_issue']}"

**STEP-BY-STEP INSTRUCTIONS**

**Step 1: Get Package Information**
- Look for package info from previous issue_analyzer agent output in conversation
- If not found, use configuration variables: PACKAGE_NAME="{config['package']}", VERSION="{config['version']}", BRANCH="{config['dist_git_branch']}"
- Verify you have all three values (PACKAGE_NAME, VERSION, BRANCH)
- If missing any values, clearly state what's needed and stop

**Step 2: Check Current Version**
- Use CodeAgent to curl the .spec file from the repository.
- Look for "Version:" field in the .spec file
- Compare current version with target VERSION
- **Decision**: Output "VERSION_CHECK_DECISION: NO_UPDATE_NEEDED" if versions match, "UPDATE_REQUIRED" if update needed, "ERROR" if issues

**Step 3: Package Update** (Only if UPDATE_REQUIRED)
- Use CodeAgent to create working directory: `mkdir -p /tmp/package-update-work && cd /tmp/package-update-work && pwd`
- Clone repository: `cd /tmp/package-update-work && git clone {config['git_url']}/[PACKAGE_NAME].git && cd [PACKAGE_NAME] && pwd && ls -la`
- Create update branch: `cd /tmp/package-update-work/[PACKAGE_NAME] && git checkout -b automated-packaging-update-[VERSION]`
- Update .spec file Version and Release fields: `cd /tmp/package-update-work/[PACKAGE_NAME] && ls *.spec`
- Create changelog entry with "Resolves: {config['jira_issue']}"
- Download sources: `cd /tmp/package-update-work/[PACKAGE_NAME] && spectool -g -S [package].spec`

**Step 4: Validation** (Only if Step 3 completed)
- Run rpmlint: `cd /tmp/package-update-work/[PACKAGE_NAME] && rpmlint [package].spec`
- Generate SRPM: `cd /tmp/package-update-work/[PACKAGE_NAME] && rpmbuild -bs [package].spec`
- Fix any errors found using the same `cd /tmp/package-update-work/[PACKAGE_NAME] && [command]` pattern

**Step 5: Output Results**
- Provide structured summary with VERSION_CHECK_DECISION, UPDATE_STATUS, STEPS_COMPLETED, COMMANDS_EXECUTED, VALIDATION_RESULTS
"""

def create_package_updater_agent():
    """Factory function to create package updater agent."""
    config = get_config()
    model = config['model']

    # Code execution specialist agent - uses built-in code executor for shell commands
    coding_agent = Agent(
        model=model,
        name='CodeAgent',
        instruction='You are a specialist in code execution. Execute shell commands for git operations, package building, and file manipulation.',
        code_executor=BuiltInCodeExecutor(),
    )

    # Search specialist agent - uses Google search for finding package information
    search_agent = Agent(
        model=model,
        name='SearchAgent',
        instruction='You are a specialist in web search. Search for package information, upstream versions, source URLs, documentation and everything else you need.',
        tools=[google_search],
    )

    # Root agent that coordinates both specialists
    return Agent(
        name="version_checker_updater",
        model=model,
        description="Checks package versions and performs updates if needed",
        instruction=create_package_updater_prompt(config),
        tools=[agent_tool.AgentTool(agent=coding_agent), agent_tool.AgentTool(agent=search_agent)],
        output_key="version_check_and_update_result",
    )
