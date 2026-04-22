---
type: context
project: agent_workflow
---

# Agent Workflow (Long-term Goal)

**File:** `agent.py`

## Goal
Build multiple specialized agents that hand off tasks to each other — orchestrator + specialists pattern.

## Current state
Basic agent loop with a `calculator` tool. Uses `claude-sonnet-4-6`. Standard tool-use loop (messages → tool call → result → continue).

## Architecture target
- Modular agents, each with a focused toolset
- Orchestrator agent routes tasks to specialists
- Agents can call each other

## Key pattern in agent.py
```python
while True:
    response = client.messages.create(model, tools, messages)
    if stop_reason == "end_turn": break
    if stop_reason == "tool_use": run tool, append result, continue
```
