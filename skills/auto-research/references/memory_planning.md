# Memory And Planning Reference

Use this reference when improving the auto-research pipeline itself or designing
agent behavior for complex coding tasks.

## Memory Organization

Short-term memory should be a bounded working set, not a dump of every event.
Keep three views:

- Focus: records the agent must keep in active context.
- Recent trace: the latest observations and reflections.
- Scoped slices: working, episodic, semantic, procedural, and reflective records.

Long-term memory should preserve durable records with:

- Scope: where the memory belongs.
- Kind: observation, reflection, decision, source, validation, procedure, or fact.
- Importance: how useful the memory is expected to be later.
- Confidence: how trustworthy it is.
- Tags: project, feature, topic, source, and task markers.
- Access metadata: last access time and access count.

Promotion rules:

- Episodic observations stay raw until they prove reusable.
- Procedural memory stores repeatable workflows and commands.
- Semantic memory stores stable project facts and design decisions.
- Reflective memory stores lessons, risks, and mistakes.
- Consolidation should prefer precision over volume.

## Classical Retrieval

Default retrieval should avoid embeddings and combine:

- BM25 for lexical relevance.
- Exact tag, kind, and scope filters.
- Recency boost for recently useful context.
- Importance boost for durable high-value memories.
- Token-overlap diversification to reduce duplicate context.

Recommended retrieval modes:

- Task start: semantic + procedural + reflective memories.
- During execution: focused short-term memory + recent episodic observations.
- Before reflection: observations + validation records + prior reflective lessons.
- Before implementation: procedural memories + similar decisions + known risks.
- After implementation: consolidate useful observations into procedural,
  semantic, or reflective memory.

## Planning Shapes

Use a linear plan for small known work.

Use a tree plan when building:

- Root: user goal.
- Branches: features or subsystems.
- Leaves: implementation tasks with validation.

Use a graph plan when researching or designing:

- Nodes: scope, evidence, alternatives, strategy, implementation, validation, reflection.
- Edges: dependency, blocks, supports, contradicts, or verifies.
- Execute dependency-ready nodes first.

Graph plans work better for uncertain tasks because evidence can change the next
useful node. Tree plans work better once the architecture is settled and work can
be decomposed into implementation leaves.

Plan lint checks:

- Every step has a stable id, goal, method, and success criteria.
- Every dependency edge references real nodes.
- Dependency graphs must be acyclic for execution.
- Graph plans should have explicit edges.

## Reflection Gates

Before claiming completion, verify:

- The plan has no unfinished required nodes.
- Risks and assumptions are named.
- Tests or validation commands ran, or missing validation is explicit.
- Retrieved memories are relevant enough to justify their context cost.
- New lessons were saved as reflective or procedural memory when reusable.

## Long-Running Research

A long-running research loop needs state outside the model context:

- Run id and task.
- Current plan graph.
- Step statuses and observations.
- Last reflection and confidence.
- Memory checkpoint boundaries.
- Status: active, waiting, complete, or failed.
- Error, retry, and wakeup metadata.

Use checkpointed stepping when:

- The task spans multiple agent turns.
- A provider call may be slow or flaky.
- The agent needs to wait for browser actions, external tools, or human input.
- The plan should be reviewed between steps.

Future design targets:

- Scheduler/heartbeat integration.
- Explicit wait events for human/tool/browser dependencies.
- Budget and deadline policies.
- Retry/backoff policies per provider.
- Compaction from raw run trace into durable memory.
