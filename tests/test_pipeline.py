from auto_research.memory import LongTermMemory, MemoryQuery, MemoryRecord, MemoryScope
from auto_research.pipeline import ResearchPipeline
from auto_research.planning import Plan, PlanEdge, PlanShape, PlanStep, StepStatus, lint_plan
from auto_research.consolidation import consolidate_memory
from auto_research.context import PromptAssembler
from auto_research.run_state import RunStatus, RunStore
from auto_research.verifier import DeterministicVerifier
from auto_research.workbench import render_run_brief


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


def test_run_state_can_checkpoint_and_resume(tmp_path):
    memory = LongTermMemory(tmp_path / "memory.sqlite")
    store = RunStore(tmp_path / "runs")
    try:
        pipeline = ResearchPipeline(memory)
        state = pipeline.start("Long running research about memory planning", max_steps=4)
        state = pipeline.step(state)
        store.save(state)

        restored = store.load(state.run_id)
        assert restored.steps_executed == 1

        resumed = pipeline.step(restored)
        store.save(resumed)
    finally:
        memory.close()

    assert resumed.steps_executed == 2
    assert resumed.status in {RunStatus.ACTIVE, RunStatus.WAITING, RunStatus.COMPLETE}
    assert resumed.events
    assert "Run the next step" in resumed.next_action() or resumed.status is not RunStatus.ACTIVE


def test_run_brief_contains_events_and_next_action(tmp_path):
    memory = LongTermMemory(tmp_path / "memory.sqlite")
    try:
        pipeline = ResearchPipeline(memory)
        state = pipeline.start("Build an agent workbench", max_steps=2)
        state = pipeline.step(state)
        brief = render_run_brief(state, pipeline.report_from_state(state))
    finally:
        memory.close()

    assert "Auto-Research Run Brief" in brief
    assert "Next Action" in brief
    assert "Recent Events" in brief
    assert "step_completed" in brief


def test_prompt_assembler_exposes_fixed_and_variable_layers(tmp_path):
    memory = LongTermMemory(tmp_path / "memory.sqlite")
    try:
        pipeline = ResearchPipeline(memory)
        state = pipeline.start("Assemble deterministic model view", max_steps=2)
        step = state.plan.ready_steps()[0]
        context = PromptAssembler().assemble(state, step, [])
    finally:
        memory.close()

    assert "Role Profile" in context.content
    assert "Task Specification" in context.content
    assert "Memory Recall" in context.content
    assert context.cache_key
    assert "role_profile" in context.fixed_layers
    assert "state_context" in context.variable_layers


def test_pipeline_writes_prompt_artifact_and_verifies_step(tmp_path):
    memory = LongTermMemory(tmp_path / "memory.sqlite")
    prompt_dir = tmp_path / "prompts"
    try:
        pipeline = ResearchPipeline(memory, prompt_dir=prompt_dir)
        state = pipeline.start("Verify prompt artifacts", max_steps=2)
        state = pipeline.step(state)
    finally:
        memory.close()

    prompt_files = list(prompt_dir.glob(f"{state.run_id}/*.md"))
    assert prompt_files
    assert "Role Profile" in prompt_files[0].read_text(encoding="utf-8")
    assert any(event.type == "prompt_assembled" for event in state.events)
    assert any(event.type == "verification_passed" for event in state.events)


def test_pipeline_supports_external_agent_completion(tmp_path):
    memory = LongTermMemory(tmp_path / "memory.sqlite")
    prompt_dir = tmp_path / "prompts"
    try:
        pipeline = ResearchPipeline(memory, prompt_dir=prompt_dir)
        state = pipeline.start("Let coding agent execute the step", max_steps=2)
        prompt = pipeline.prepare_agent_step(state)
        assert prompt is not None
        state = pipeline.complete_agent_step(
            state,
            prompt.step_id,
            "The coding agent inspected the prompt, executed local tools, and produced a substantial observation.",
        )
    finally:
        memory.close()

    assert state.steps_executed == 1
    assert any(event.type == "verification_passed" for event in state.events)
    assert list(prompt_dir.glob(f"{state.run_id}/*.md"))


def test_deterministic_verifier_rejects_empty_observation(tmp_path):
    memory = LongTermMemory(tmp_path / "memory.sqlite")
    try:
        pipeline = ResearchPipeline(memory)
        state = pipeline.start("Verify bad observation", max_steps=1)
        step = state.plan.ready_steps()[0]
        step.status = StepStatus.COMPLETE
        report = DeterministicVerifier().verify_step(state, step, "")
    finally:
        memory.close()

    assert not report.passed
