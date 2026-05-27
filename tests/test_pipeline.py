from auto_research.memory import LongTermMemory, MemoryQuery, MemoryRecord, MemoryScope
from auto_research.pipeline import ResearchPipeline
from auto_research.planning import Plan, PlanEdge, PlanShape, PlanStep, lint_plan
from auto_research.consolidation import consolidate_memory


def test_pipeline_produces_report(tmp_path):
    memory = LongTermMemory(tmp_path / "memory.sqlite")
    try:
        report = ResearchPipeline(memory).run("Build a coding-agent research loop", max_steps=3)
    finally:
        memory.close()

    assert report.task == "Build a coding-agent research loop"
    assert len(report.plan.steps) == 4
    assert report.plan.shape in {PlanShape.TREE, PlanShape.GRAPH}
    assert report.observations
    assert "Research Report" in report.to_markdown()


def test_long_term_memory_is_retrievable(tmp_path):
    memory = LongTermMemory(tmp_path / "memory.sqlite")
    try:
        ResearchPipeline(memory).run("Assess planning and reflection risks", max_steps=2)
        results = memory.search("reflection risks")
    finally:
        memory.close()

    assert results


def test_report_contains_only_observations(tmp_path):
    memory = LongTermMemory(tmp_path / "memory.sqlite")
    try:
        report = ResearchPipeline(memory).run("Separate observations from reflection", max_steps=3)
    finally:
        memory.close()

    assert all(record.kind == "observation" for record in report.observations)


def test_memory_retrieval_uses_scope_and_bm25(tmp_path):
    memory = LongTermMemory(tmp_path / "memory.sqlite")
    try:
        memory.add(
            MemoryRecord(
                "Use BM25 and lexical diversification for coding-agent memory retrieval.",
                scope=MemoryScope.PROCEDURAL,
                importance=0.9,
                tags=("retrieval",),
            )
        )
        memory.add(
            MemoryRecord(
                "A visual design note unrelated to planning.",
                scope=MemoryScope.EPISODIC,
                tags=("design",),
            )
        )
        results = memory.retrieve(
            MemoryQuery(
                text="BM25 memory retrieval",
                scopes=(MemoryScope.PROCEDURAL,),
                tags=("retrieval",),
            )
        )
    finally:
        memory.close()

    assert results
    assert results[0].record.scope is MemoryScope.PROCEDURAL
    assert "matched:bm25" in results[0].reasons


def test_memory_consolidation_promotes_reusable_records(tmp_path):
    memory = LongTermMemory(tmp_path / "memory.sqlite")
    try:
        memory.add(
            MemoryRecord(
                "Use BM25 retrieval workflow before adding embeddings.",
                scope=MemoryScope.EPISODIC,
                kind="observation",
                tags=("retrieval",),
            )
        )
        report = consolidate_memory(memory)
    finally:
        memory.close()

    assert report.promoted
    assert report.promoted[0].scope is MemoryScope.PROCEDURAL


def test_plan_lint_detects_cycles():
    plan = Plan(
        task="cycle",
        steps=[
            PlanStep("a", "A", "Do A", "A done"),
            PlanStep("b", "B", "Do B", "B done"),
        ],
        edges=[
            PlanEdge("a", "b"),
            PlanEdge("b", "a"),
        ],
    )

    issues = lint_plan(plan)

    assert any(issue.severity == "error" and "cycle" in issue.message for issue in issues)
