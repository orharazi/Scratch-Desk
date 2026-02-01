# Scratch-Desk Custom Agents

Custom agents for the Scratch-Desk CNC control system.

## Available Agents

| Agent | Model | Color | Use Case |
|-------|-------|-------|----------|
| `tech-lead` | opus | green | General CNC programming guidance |
| `hardware-debug` | sonnet | red | Arduino/GPIO/RS485 troubleshooting |
| `grbl-expert` | sonnet | yellow | Motor control and G-code |
| `step-generator` | sonnet | blue | Execution step modification |
| `gui-developer` | sonnet | purple | Tkinter GUI development |
| `safety-system` | opus | orange | Safety interlocks and collision prevention |
| `config-manager` | haiku | cyan | settings.json management |

## All Agents Have Access To
- `Read` - Read files
- `Write` - Write files
- `Edit` - Edit files
- `Glob` - Find files by pattern
- `Grep` - Search file contents
- `Bash` - Run shell commands
- `Task` - Spawn sub-agents
- `WebFetch` - Fetch web content
- `WebSearch` - Search the web

## How to Use

Invoke an agent with the `/agent` command:

```
/agent:hardware-debug "RS485 sensors not responding"
/agent:grbl-expert "Add a new homing sequence"
/agent:safety-system "Add collision detection for Z-axis"
```

## Agent Format

```yaml
---
name: agent-name
description: Short description
model: sonnet|opus|haiku
color: red|blue|green|etc
allowedTools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task
  - WebFetch
  - WebSearch
---

Agent instructions here...
```
