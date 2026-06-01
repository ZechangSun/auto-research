from __future__ import annotations

from dataclasses import dataclass

from auto_research.planning import PlanStep, lint_plan
from auto_research.run_state import ResearchRunState


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    passed: bool
    message: str


@dataclass(frozen=True)
class VerificationReport:
    checks: tuple[VerificationCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def summary(self) -> str:
        status = "pass" if self.passed else "fail"
        details = "; ".join(f"{check.name}={check.passed}" for check in self.checks)
        return f"verification={status}: {details}"


class DeterministicVerifier:
    """Machine-authoritative checks that do not call a model."""

    def verify_step(
        self,
        state: ResearchRunState,
        step: PlanStep,
        observation: str,
    ) -> VerificationReport:
        issues = lint_plan(state.plan)
        error_issues = [issue for issue in issues if issue.severity == "error"]
        checks = (
            VerificationCheck(
                "correctness",
                bool(observation and len(observation.strip()) >= 20),
                "Observation is non-empty and substantial.",
            ),
            VerificationCheck(
                "completeness",
                step.status.value == "complete" and bool(step.observation),
                "Step is marked complete and has an observation.",
            ),
            VerificationCheck(
                "integrity",
                not error_issues,
                "Plan has no deterministic lint errors.",
            ),
        )
        return VerificationReport(checks=checks)
