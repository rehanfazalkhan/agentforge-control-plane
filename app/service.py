"""Application service orchestrating policy, agents, telemetry and evaluations."""

from __future__ import annotations

import time
from collections import deque
from uuid import uuid4

from .agents import execute_specialist
from .evaluation import evaluate
from .models import AgentRun, Overview, RunRequest, RunStatus, TraceSpan
from .policy import PolicyViolation, validate_input


class AgentForgeService:
    def __init__(self) -> None:
        self._runs: deque[AgentRun] = deque(maxlen=50)

    def run(self, request: RunRequest) -> AgentRun:
        started = time.perf_counter()
        trace = [TraceSpan(name="request.validate", kind="policy", duration_ms=1)]
        run_id = str(uuid4())
        try:
            validate_input(request.question)
            trace.append(TraceSpan(name="supervisor.route", kind="agent", duration_ms=1))
            result = execute_specialist(request.question, request.actor_role)
            trace.append(
                TraceSpan(
                    name="specialist.execute", kind="agent", duration_ms=1,
                    attributes={"route": result.route, "tool_count": len(result.tool_calls)},
                )
            )
            for tool_call in result.tool_calls:
                trace.append(
                    TraceSpan(
                        name=f"tool.{tool_call.name}", kind="tool",
                        duration_ms=tool_call.duration_ms,
                        attributes={"policy_decision": tool_call.policy_decision},
                    )
                )
            run = AgentRun(
                id=run_id, question=request.question, actor_role=request.actor_role,
                status=RunStatus.COMPLETED, route=result.route, response=result.response,
                citations=result.citations, tool_calls=result.tool_calls, trace=trace,
                latency_ms=max(1, round((time.perf_counter() - started) * 1000)),
            )
        except PolicyViolation as error:
            trace.append(
                TraceSpan(name="request.blocked", kind="policy", duration_ms=1, attributes={"reason": str(error)})
            )
            run = AgentRun(
                id=run_id, question=request.question, actor_role=request.actor_role,
                status=RunStatus.BLOCKED, route="policy", response=str(error), trace=trace,
                latency_ms=max(1, round((time.perf_counter() - started) * 1000)),
            )
        run.evaluations = evaluate(run)
        self._runs.appendleft(run)
        return run

    def runs(self) -> list[AgentRun]:
        return list(self._runs)

    def overview(self) -> Overview:
        runs = list(self._runs)
        if not runs:
            return Overview(total_runs=0, success_rate=0, average_latency_ms=0, policy_blocks=0, evaluation_pass_rate=0)
        completed = sum(run.status == RunStatus.COMPLETED for run in runs)
        blocks = sum(run.status == RunStatus.BLOCKED for run in runs)
        evaluations = [score for run in runs for score in run.evaluations]
        passed = sum(score.passed for score in evaluations)
        return Overview(
            total_runs=len(runs),
            success_rate=round(completed / len(runs) * 100, 1),
            average_latency_ms=round(sum(run.latency_ms for run in runs) / len(runs)),
            policy_blocks=blocks,
            evaluation_pass_rate=round(passed / len(evaluations) * 100, 1) if evaluations else 0,
        )
