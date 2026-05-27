---
name: auto-research
description: Use this skill when a coding agent needs to research, plan, implement, reflect, or improve a repository with persistent memory. Trigger for complex coding tasks, repository self-improvement, architecture investigation, long-running implementation work, and tasks that benefit from short-term memory, long-term memory, planning, and reflection.
---

# Auto-Research

Use this skill to add a research loop around coding-agent work.

## Core Workflow

1. Start with repository context.
   - For repo improvement: `auto-research improve --repo . --max-steps 5`
   - For a specific task: `auto-research run "<task>" --max-steps 5`
2. Read the generated report or `.auto_research/improvement_brief.md`.
3. Convert the highest-value recommendation into a small implementation plan.
4. Implement the change with normal coding-agent tools.
5. Run relevant tests.
6. Run the pipeline again when the task is substantial or the results changed the direction.

## Memory

- Long-term memory is stored in `.auto_research/memory.sqlite`.
- Short-term memory lives in the current pipeline run.
- Do not commit `.auto_research/`; it is local agent memory.
- Use `--session-id` to group related work across multiple runs.

## Decision Rules

- Prefer the smallest change that improves future agent usefulness.
- Keep orchestration separate from provider implementations.
- Add provider protocols before binding the pipeline to one search, model, browser, or coding-agent backend.
- Reflection should name gaps, risks, and validation steps before claiming completion.
- If the report conflicts with direct repo evidence, trust the repo evidence and update the pipeline or memory.

## Useful Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
auto-research improve --repo .
auto-research run "Research how to implement this coding task"
python -m pytest
```

## Expected Output

The skill should leave the agent with:

- A clear task framing.
- A plan with completed or pending steps.
- Observations grounded in available context.
- A reflection with confidence, gaps, and next actions.
- A small next implementation target.
