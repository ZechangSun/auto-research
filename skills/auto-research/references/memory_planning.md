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

## Reflection Gates

Before claiming completion, verify:

- The plan has no unfinished required nodes.
- Risks and assumptions are named.
- Tests or validation commands ran, or missing validation is explicit.
- Retrieved memories are relevant enough to justify their context cost.
- New lessons were saved as reflective or procedural memory when reusable.
