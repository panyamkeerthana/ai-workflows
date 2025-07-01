#!/usr/bin/env python3
"""
Minimal agent runner for ADK sub-agents.
Executes the selected agent based on AGENT_TYPE environment variable.
"""
import asyncio
import os
import sys
import logging
import traceback
from datetime import datetime

from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import agent_tool
from google.genai import types

from issue_analyzer import create_issue_analyzer_agent, mcp_connection
from package_updater import create_package_updater_agent

def get_model() -> str:
    """Get model from environment with consistent default."""
    return os.environ.get('MODEL', 'gemini-2.5-flash')

def setup_logging():
    """Set up simple logging for tool usage tracking."""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    return logging.getLogger('adk_runner')

async def run_centos_agent():
    """Run the selected agent based on AGENT_TYPE environment variable."""
    logger = setup_logging()

    agent_type = os.environ.get('AGENT_TYPE', 'issue_analyzer')
    logger.info(f"Starting agent: {agent_type}")

    # Create the selected agent using factory functions (will be recreated with MCP tools if needed)
    if agent_type == 'issue_analyzer':
        agent = None  # Will be created with MCP tools
    elif agent_type == 'package_updater':
        agent = create_package_updater_agent()
    elif agent_type == 'pipeline':
        agent = None  # Will be created with MCP tools
        logger.info("Will create SequentialAgent pipeline with MCP tools")
    else:
        logger.error(f"Unknown AGENT_TYPE '{agent_type}'. Must be 'issue_analyzer', 'package_updater', or 'pipeline'")
        sys.exit(1)

    await run_single_agent(logger, agent, agent_type)



async def run_single_agent(logger, agent, agent_type):
    """Run a single agent with proper MCP lifecycle management."""
    session_service = InMemorySessionService()
    APP_NAME = "centos_package_updater"
    USER_ID = f"user_1_{agent_type}"
    SESSION_ID = f"session_001_{agent_type}"

    session = await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    logger.info(f"Created session: {SESSION_ID}")

    # For agents that need MCP tools, use proper lifecycle management
    if agent_type == 'issue_analyzer' or agent_type == 'pipeline':
        # Use MCP connection with proper async context management
        async with mcp_connection() as mcp_tools:
            logger.info("MCP connection established")

            # Recreate agents with MCP tools built-in
            if agent_type == 'issue_analyzer':
                agent = create_issue_analyzer_agent(mcp_tools=mcp_tools)
                logger.info(f"Created issue_analyzer agent: {agent.name}")
            elif agent_type == 'pipeline':
                # Create fresh agent instances with MCP tools for issue_analyzer
                issue_analyzer = create_issue_analyzer_agent(mcp_tools=mcp_tools)
                package_updater = create_package_updater_agent()

                agent = SequentialAgent(
                    name="centos_package_pipeline_update_workflow",
                    description="A sequential workflow for CentOS package updating: issue analysis → version check and package update",
                    sub_agents=[issue_analyzer, package_updater]
                )
                logger.info(f"Created pipeline agent: {agent.name} with {len(agent.sub_agents)} sub-agents")

            # Now run the agent with MCP tools properly integrated
            await _run_agent_with_session(logger, agent, session_service, session,
                                        APP_NAME, USER_ID, SESSION_ID, agent_type)

        logger.info("MCP connection properly closed")
    else:
        # Package updater doesn't need MCP
        logger.info(f"Using package_updater agent: {agent.name}")
        await _run_agent_with_session(logger, agent, session_service, session,
                                    APP_NAME, USER_ID, SESSION_ID, agent_type)


async def _run_agent_with_session(logger, agent, session_service, session,
                                APP_NAME, USER_ID, SESSION_ID, agent_type):
    """Helper function to run agent with session."""
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    logger.info("Runner initialized, starting execution...")

    # Create appropriate initial message based on agent type
    initial_messages = {
        'pipeline': "Start the full CentOS package update pipeline. First analyze the configured JIRA issue, then proceed with the package update workflow.",
        'issue_analyzer': "Start the JIRA issue analysis now. Use the configured JIRA issue key and fetch it using the available JIRA tools.",
        'package_updater': "Start the CentOS package update process. Check for package updates and perform the necessary update operations."
    }
    initial_message = initial_messages.get(agent_type, "Start the agent execution.")

    content = types.Content(role="user", parts=[types.Part(text=initial_message)])


    async for event in runner.run_async(
        user_id=USER_ID, session_id=SESSION_ID, new_message=content
    ):

        if event.is_final_response() and event.content and event.content.parts:
            logger.info("\n" + "="*60)
            logger.info("AGENT RESPONSE:")
            logger.info("="*60)
            logger.info(event.content.parts[0].text)


    logger.info("Cleaning up runner and session...")
    try:
        await runner.close()
    except Exception as cleanup_error:
        # Log but don't fail on cleanup errors (often non-fatal)
        logger.debug(f"Cleanup warning: {cleanup_error}")

    try:
        await session_service.delete_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )
    except Exception as session_error:
        logger.debug(f"Session cleanup warning: {session_error}")

# Ensures this runs only when script is executed directly
if __name__ == "__main__":
    try:
        asyncio.run(run_centos_agent())
    except Exception as e:
        logger = logging.getLogger('adk_runner')
        logger.error(f"Execution failed: {str(e)}")
        logger.debug(traceback.format_exc())
        sys.exit(1)
