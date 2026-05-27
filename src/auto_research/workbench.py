from __future__ import annotations

from auto_research.pipeline import ResearchReport
from auto_research.run_state import ResearchRunState


def render_run_brief(state: ResearchRunState, report: ResearchReport | None = None) -> str:
    lines = [
        "# Auto-Research Run Brief",
        "",
        f"Run: {state.run_id}",
        f"Status: {state.status.value}",
        f"Steps: {state.steps_executed}/{state.max_steps}",
        f"Task: {state.task}",
        "",
        "## Next Action",
        state.next_action(),
        "",
        "## Plan",
    ]
    for step in state.plan.steps:
        dependencies = state.plan.dependencies_for(step.id)
        suffix = f" depends_on={','.join(dependencies)}" if dependencies else ""
        lines.append(f"- [{step.status.value}] {step.id}: {step.goal}{suffix}")
    if state.last_error:
        lines.extend(["", "## Last Error", state.last_error])
    lines.extend(["", "## Recent Events"])
    recent_events = state.events[-10:]
    if recent_events:
        for event in recent_events:
            step = f" step={event.step_id}" if event.step_id else ""
            lines.append(f"- {event.created_at} [{event.type}]{step}: {event.message}")
    else:
        lines.append("- None")
    if report:
        lines.extend(["", "## Reflection", report.reflection.summary, f"Confidence: {report.reflection.confidence:.2f}"])
        if report.reflection.gaps:
            lines.extend(["", "## Gaps", *[f"- {gap}" for gap in report.reflection.gaps]])
    return "\n".join(lines)
