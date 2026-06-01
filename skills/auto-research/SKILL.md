---
name: auto-research
description: Use this skill when a coding agent needs to research, plan, implement, reflect, or improve a repository with persistent memory. Trigger for complex coding tasks, repository self-improvement, architecture investigation, long-running implementation work, and tasks that benefit from short-term memory, long-term memory, planning, and reflection.
---

# Auto-Research

Use this skill to add a research loop around coding-agent work.

For detailed memory/retrieval/planning design, read
`references/memory_planning.md` when the task is about improving this pipeline or
designing complex agent behavior.

## Core Workflow

1. Start with repository context.
   - For repo improvement: `auto-research improve --repo . --max-steps 5`
   - For a specific task: `auto-research run "<task>" --max-steps 5`
   - For long-running work: `auto-research runs start "<task>" --max-steps 12`
2. Read the generated report or `.auto_research/improvement_brief.md`.
3. Convert the highest-value recommendation into a small implementation plan.
4. Implement the change with normal coding-agent tools.
5. Run relevant tests.
6. Consolidate reusable lessons: `auto-research memory consolidate`.
7. Run the pipeline again when the task is substantial or the results changed the direction.

## Long-Running Work

Use checkpointed runs when the task may exceed one turn, wait on tools, or need
periodic reflection:

```bash
auto-research runs start "Research and implement the feature" --max-steps 12
auto-research runs brief <run-id>
auto-research runs step <run-id> --steps 3
auto-research runs status <run-id>
auto-research runs list
```

Use `brief` at the start of each work interval. It is the agent-facing equipment
view: task, status, next action, plan progress, recent events, reflection, and
gaps.

Each step assembles a deterministic model-view prompt file. Treat that file as
the subagent/bootstrap input:

- Fixed layers: role profile, task specification, output format.
- Variable layers: reference injection, plan, memory recall, state context.
- Default location: `.auto_research/runs/prompts/<run-id>/`.

Run one or more checkpointed steps per wakeup or work interval. After each step,
inspect status:

- `active`: continue stepping.
- `waiting`: needs another wakeup, higher max step budget, or external input.
- `complete`: produce final summary and consolidate memory.
- `failed`: inspect `last_error`, fix the provider/tool issue, then resume.

Use `--steps N` for bounded progress and `--until-complete` only when the
provider is deterministic enough to run unattended.

Long-running limitations to remember:

- Current checkpoints are local JSON files.
- There is no built-in scheduler yet.
- Human approvals and external tool waits are not first-class events yet.
- Budget, deadline, cancellation, and retry policies still need design.

## Equipment Pattern

For substantial coding work:

1. Start or resume a run.
2. Read `runs brief`.
3. Execute a small number of steps.
4. Implement the next concrete change with normal coding tools.
5. Run tests.
6. Remember or consolidate reusable lessons.
7. Leave the run status and next action clear for the next wakeup.

## Goal Loop Model

Use this mental model:

- Goal Loop: persistent orchestrator and checkpoint owner.
- Planner: creates objectives, dependencies, and retrieval hints.
- Recall: retrieves relevant memory before execution.
- Context Assembler: writes the per-round prompt file.
- Executor: runs the current step and returns a focused observation.
- Review: reflects on confidence, gaps, and next action.
- Verifier: deterministic correctness/completeness/integrity gate.
- Archive: stores observations, reflections, verifier output, and reusable lessons.

When verifier output fails, pause and repair the plan, context, or executor
before continuing.

## Memory

- Long-term memory is stored in `.auto_research/memory.sqlite`.
- Short-term memory lives in the current pipeline run and should keep focused records separate from the full trace.
- Do not commit `.auto_research/`; it is local agent memory.
- Use `--session-id` to group related work across multiple runs.
- Use `auto-research memory remember "<fact>" --scope procedural --tag workflow` when the agent learns a durable method.
- Use `auto-research memory search "<query>" --scope procedural` before repeating a complex workflow.
- Use `auto-research memory consolidate` after substantial work.
- Prefer scoped memory:
  - `working` for active task facts.
  - `episodic` for run observations.
  - `semantic` for durable project facts.
  - `procedural` for reusable methods.
  - `reflective` for lessons and risks.

## Retrieval

Use classical retrieval before reaching for model context:

- BM25-style lexical search for relevance.
- Scope, kind, and tag filters for precision.
- Importance and recency boosts for salience.
- Token-overlap diversification to avoid duplicate memories.
- No embeddings are required by default.

## Planning

- Use a linear plan only for small, familiar tasks.
- Use a tree plan for implementation work that decomposes into subfeatures.
- Use a graph plan for research, architecture, comparison, or uncertain tasks.
- Execute dependency-ready nodes first.
- Reflect after each meaningful node and update the plan when new evidence changes the route.
- Lint plans for missing criteria, invalid edges, and cycles before trusting them.

## Decision Rules

- Understand the task before planning; write down assumptions when the request is ambiguous.
- Create or refine a brief spec for nontrivial work.
- Prefer the smallest change that improves future agent usefulness.
- Keep orchestration separate from provider implementations.
- Add provider protocols before binding the pipeline to one search, model, browser, or coding-agent backend.
- Reflection should name gaps, risks, and validation steps before claiming completion.
- If the report conflicts with direct repo evidence, trust the repo evidence and update the pipeline or memory.
- Promote only reusable lessons. Do not turn one-off task details into procedural memory.

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
