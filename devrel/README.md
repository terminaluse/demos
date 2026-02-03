# DevRel Intelligence Agent

Example demonstrating **skills mounting** with the Claude Agent SDK.

## Skills Mounting

Skills are mounted into the agent's sandbox at runtime:

1. **Dockerfile** copies skills into the image:
   ```dockerfile
   COPY devrel/skills /app/devrel/skills
   ```

2. **config.yaml** mounts them into the sandbox:
   ```yaml
   sandbox:
     mounts:
       - source: skills                    # Path in image
         target: /root/.claude/skills      # Path in sandbox
         readonly: true
   ```

3. **agent.py** loads them via `setting_sources`:
   ```python
   options = ClaudeAgentOptions(
       setting_sources=["user"],  # Loads skills from /root/.claude/skills
   )
   ```

## Included Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| hackernews | `/hn` | Search HN stories and comments |
| reddit-research | `/reddit-research` | Search Reddit posts and comments |
| x-research | `/x-research` | Search X/Twitter |
| youtube-research | `/youtube-research` | Search YouTube videos and comments |
| slack-tools | `/slack-tools` | Post findings to Slack |

## Running

```bash
terminaluse agents run --config config.yaml
```

## Environment Variables

Copy `.env.example` to `.env` and add API keys for the platforms you want to search.
