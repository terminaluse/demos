"""DevRel Intelligence Agent.

This agent helps dev rel teams understand what developers are saying about a product.
It monitors HN, Reddit, X, and YouTube to surface documentation gaps, pain points,
competitor mentions, and resonant content.
"""

from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import ResultMessage

from terminaluse import (
    AgentServer,
    TaskContext,
    adk,
    make_logger,
)
from terminaluse.types import Event, TextContent

logger = make_logger(__name__)

SYSTEM_PROMPT = """You are a DevRel Intelligence Agent that helps developer relations teams understand what developers are saying about their product.

## Your Jobs To Be Done

1. **Find Documentation Gaps** - What questions are developers asking that the docs don't answer?
2. **Surface Pain Points** - Find people complaining and link to their complaints
3. **Track Competitor Mentions** - What do devs say is better about competitors?
4. **Discover Resonant Content** - What dev content from other companies is working well?

## Search Strategy

- **Cast wide first**: Search across HN, Reddit, X, and YouTube in parallel
- **Then go deep**: When you find something interesting, drill down. Multiple people saying the same thing = real signal
- **Cross-validate**: If a complaint appears on both Reddit and HN, it's likely widespread
- **Follow threads**: Replies often have better insights than the original post

## Output Requirements

- Always include direct links to sources
- Quote relevant snippets with attribution
- Group findings by theme
- Note engagement (upvotes, likes, retweets) to gauge reach
- Save all research to /workspace as markdown files

## Available Skills

You have access to research tools for:
- **Hacker News** (`/hn` or `/hackernews`) - Search stories and comments, fetch threads
- **Reddit** (`/reddit-research`) - Search subreddits, posts, and comments
- **X/Twitter** (`/x-research`) - Search tweets, analyze engagement, drill into viral posts
- **YouTube** (`/youtube-research`) - Search videos, analyze comments for pain points and feature requests
- **Slack** (`/slack-tools`) - Post findings to team channels

## Workflow

1. Start with a broad search across all platforms in parallel
2. Identify recurring themes and high-engagement content
3. Drill down into interesting threads for deeper insights
4. Cross-reference findings across platforms
5. Compile findings into a structured markdown report
6. Save report to /workspace with a descriptive filename
"""

# Create an agent server
server = AgentServer()


@server.on_create
async def handle_create(ctx: TaskContext, params: dict[str, Any]):
    """Handle task creation.
    """
    # Initialize state - session_id will be set after first query
    await ctx.state.create(
        state={
            "session_id": None,
        },
    )


@server.on_event
async def handle_event(ctx: TaskContext, event: Event):
    """Handle incoming messages from users.

    Routes messages to Claude and streams responses back.
    """
    try:
        # Parse user message
        if not isinstance(event.content, TextContent):
            raise ValueError("Unsupported message type. Only text messages are supported.")
        user_message = event.content.content

        # Get state for to get the session ID
        state = await ctx.state.get()
        session_id = state.get("session_id") if state else None

        # Configure Claude Agent SDK
        options = ClaudeAgentOptions(
            include_partial_messages=True, # enable streaming
            permission_mode="bypassPermissions",
            cwd="/workspace",
            allowed_tools=["Skill", "Read", "Write", "Bash", "Edit", "Grep", "Glob"],
            setting_sources=["user"],  # Load skills from /root/.claude/skills
            resume=session_id,  # Resume previous session if exists
            system_prompt=SYSTEM_PROMPT,
        )

        # Query Claude and stream responses
        async for message in query(prompt=user_message, options=options):
            await adk.messages.send(task_id=ctx.task.id, content=message)

            # Save session ID for continuity
            if isinstance(message, ResultMessage):
                await ctx.state.update(
                    {"session_id": message.session_id}
                )

    except Exception as e:
        error_msg = str(e)
        await ctx.messages.send(f"Sorry, I encountered an error: {error_msg}")


@server.on_cancel
async def handle_cancel(ctx: TaskContext):
    """Handle task cancellation.

    Clean up any resources or state when a task is cancelled.
    """
    logger.info(f"Task cancelled: {ctx.task.id}")