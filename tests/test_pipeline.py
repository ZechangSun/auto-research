from auto_research.memory import LongTermMemory
from auto_research.pipeline import ResearchPipeline


def test_pipeline_produces_report(tmp_path):
    memory = LongTermMemory(tmp_path / "memory.sqlite")
    try:
        report = ResearchPipeline(memory).run("Build a coding-agent research loop", max_steps=3)
    finally:
        memory.close()

    assert report.task == "Build a coding-agent research loop"
    assert len(report.plan.steps) == 3
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
