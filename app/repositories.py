"""Run persistence with an in-memory development store and DynamoDB production store."""

from __future__ import annotations

from collections import deque
from typing import Protocol

from .config import Settings
from .models import AgentRun


class RunRepository(Protocol):
    def save(self, run: AgentRun) -> None: ...

    def list_recent(self, limit: int = 50) -> list[AgentRun]: ...

    def get(self, run_id: str) -> AgentRun | None: ...


class InMemoryRunRepository:
    """Deliberately limited development store; it is never selected in production."""

    def __init__(self) -> None:
        self._runs: deque[AgentRun] = deque(maxlen=200)

    def save(self, run: AgentRun) -> None:
        self._runs = deque((item for item in self._runs if item.id != run.id), maxlen=200)
        self._runs.appendleft(run)

    def list_recent(self, limit: int = 50) -> list[AgentRun]:
        return list(self._runs)[:limit]

    def get(self, run_id: str) -> AgentRun | None:
        return next((run for run in self._runs if run.id == run_id), None)


class DynamoRunRepository:
    """DynamoDB repository using a GSI for bounded, newest-first operational queries."""

    def __init__(self, table_name: str, region_name: str) -> None:
        try:
            import boto3
        except ImportError as error:  # pragma: no cover - requires AWS dependency
            raise RuntimeError("boto3 is required for DynamoDB persistence.") from error
        self._table = boto3.resource("dynamodb", region_name=region_name).Table(table_name)

    def save(self, run: AgentRun) -> None:
        self._table.put_item(
            Item={
                "run_id": run.id,
                "gsi_pk": "RUN",
                "gsi_sk": f"{run.created_at.isoformat()}#{run.id}",
                "payload": run.model_dump_json(),
                "ttl": int(run.created_at.timestamp()) + 60 * 60 * 24 * 30,
            }
        )

    def list_recent(self, limit: int = 50) -> list[AgentRun]:
        response = self._table.query(
            IndexName="by_created",
            KeyConditionExpression="gsi_pk = :partition",
            ExpressionAttributeValues={":partition": "RUN"},
            ScanIndexForward=False,
            Limit=limit,
        )
        return [AgentRun.model_validate_json(item["payload"]) for item in response.get("Items", [])]

    def get(self, run_id: str) -> AgentRun | None:
        response = self._table.get_item(Key={"run_id": run_id})
        item = response.get("Item")
        return AgentRun.model_validate_json(item["payload"]) if item else None


def build_run_repository(settings: Settings) -> RunRepository:
    if settings.is_production:
        # Keep the process alive long enough for /readyz to report gaps. Invocations still
        # fail before execution because AgentForgeService enforces the same readiness gate.
        if settings.production_gaps():
            return InMemoryRunRepository()
        return DynamoRunRepository(settings.dynamodb_table or "", settings.aws_region)
    return InMemoryRunRepository()
