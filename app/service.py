"""Production orchestration: authenticate, execute, evaluate, persist, and audit every run."""

from __future__ import annotations

import time
from uuid import uuid4

from .agents import execute_development_specialist
from .auth import Principal
from .config import ConfigurationError, Settings
from .evaluation import evaluate
from .model_runtime import BedrockConverseEngine
from .models import AgentRun, Overview, RunRequest, RunStatus, TraceSpan
from .policy import PolicyViolation, validate_input
from .repositories import RunRepository, build_run_repository
from .telemetry import record_run
from .tools import ToolExecutor


class AgentForgeService:
    def __init__(
        self,
        settings: Settings | None = None,
        repository: RunRepository | None = None,
        model_engine: BedrockConverseEngine | None = None,
    ) -> None:
        self.settings = settings or Settings.from_environment()
        self.repository = repository or build_run_repository(self.settings)
        self.tools = ToolExecutor(self.settings)
        self.model_engine = model_engine or BedrockConverseEngine(self.settings)

    def run(self, request: RunRequest, principal: Principal | None = None) -> AgentRun:
        if principal is None:
            principal = Principal("local-development-user", request.actor_role)
        started = time.perf_counter()
        run_id = str(uuid4())
        trace = [TraceSpan(name="request.validate", kind="policy", duration_ms=1)]
        try:
            validate_input(request.question)
            trace.append(
                TraceSpan(
                    name="supervisor.dispatch",
                    kind="agent",
                    duration_ms=1,
                    attributes={"runtime_mode": self.settings.runtime_mode},
                )
            )
            if self.settings.is_production:
                self.settings.assert_ready_for_production()
                result = self.model_engine.execute(request.question, principal, self.tools)
            else:
                result = execute_development_specialist(request.question, principal, self.tools)
            trace.append(
                TraceSpan(
                    name="specialist.execute",
                    kind="agent",
                    duration_ms=1,
                    attributes={"route": result.route, "tool_count": len(result.tool_calls), "model_id": result.model_id},
                )
            )
            for tool_call in result.tool_calls:
                trace.append(
                    TraceSpan(
                        name=f"tool.{tool_call.name}",
                        kind="tool",
                        duration_ms=tool_call.duration_ms,
                        attributes={"policy_decision": tool_call.policy_decision},
                    )
                )
            run = AgentRun(
                id=run_id,
                question=request.question,
                actor_id=principal.subject,
                actor_role=principal.role,
                session_id=request.session_id,
                runtime_mode=self.settings.runtime_mode,
                model_id=result.model_id,
                status=RunStatus.COMPLETED,
                route=result.route,
                response=result.response,
                citations=result.citations,
                tool_calls=result.tool_calls,
                trace=trace,
                token_usage=result.token_usage,
                latency_ms=max(1, round((time.perf_counter() - started) * 1000)),
            )
        except PolicyViolation as error:
            trace.append(TraceSpan(name="request.blocked", kind="policy", duration_ms=1, attributes={"reason": str(error)}))
            run = self._terminal_run(run_id, request, principal, RunStatus.BLOCKED, "policy", str(error), trace, started)
        except (ConfigurationError, RuntimeError) as error:
            trace.append(TraceSpan(name="run.failed", kind="system", duration_ms=1, attributes={"error_type": type(error).__name__}))
            run = self._terminal_run(
                run_id,
                request,
                principal,
                RunStatus.FAILED,
                "system",
                "The request could not be completed safely. Review the trace and service configuration.",
                trace,
                started,
            )
        run.evaluations = evaluate(run)
        self.repository.save(run)
        record_run(run)
        return run

    def get_run(self, run_id: str) -> AgentRun | None:
        return self.repository.get(run_id)

    def runs(self) -> list[AgentRun]:
        return self.repository.list_recent()

    def overview(self) -> Overview:
        runs = self.runs()
        if not runs:
            return Overview(total_runs=0, success_rate=0, average_latency_ms=0, policy_blocks=0, evaluation_pass_rate=0)
        completed = sum(run.status == RunStatus.COMPLETED for run in runs)
        blocks = sum(run.status == RunStatus.BLOCKED for run in runs)
        evaluations = [score for run in runs for score in run.evaluations]
        return Overview(
            total_runs=len(runs),
            success_rate=round(completed / len(runs) * 100, 1),
            average_latency_ms=round(sum(run.latency_ms for run in runs) / len(runs)),
            policy_blocks=blocks,
            evaluation_pass_rate=round(sum(score.passed for score in evaluations) / len(evaluations) * 100, 1) if evaluations else 0,
        )

    def readiness(self) -> dict[str, object]:
        gaps = self.settings.production_gaps()
        return {
            "ready": not gaps,
            "runtime_mode": self.settings.runtime_mode,
            "persistence": self.settings.run_store,
            "gaps": gaps,
        }

    def _terminal_run(
        self,
        run_id: str,
        request: RunRequest,
        principal: Principal,
        status: RunStatus,
        route: str,
        response: str,
        trace: list[TraceSpan],
        started: float,
    ) -> AgentRun:
        return AgentRun(
            id=run_id,
            question=request.question,
            actor_id=principal.subject,
            actor_role=principal.role,
            session_id=request.session_id,
            runtime_mode=self.settings.runtime_mode,
            status=status,
            route=route,
            response=response,
            trace=trace,
            latency_ms=max(1, round((time.perf_counter() - started) * 1000)),
        )
