from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SourceEvidence:
    knowledge_source_name: str
    activity_count: int
    reference_count: int
    activity_types: tuple[str, ...]
    reference_types: tuple[str, ...]

    @property
    def participated(self) -> bool:
        return self.activity_count > 0 and self.reference_count > 0


@dataclass(frozen=True)
class DualSourceEvidence:
    search: SourceEvidence
    mcp: SourceEvidence

    @property
    def both_participated(self) -> bool:
        return self.search.participated and self.mcp.participated

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "both_participated": self.both_participated,
        }


def verify_dual_source_evidence(
    response: dict[str, Any],
    *,
    search_knowledge_source_name: str,
    mcp_knowledge_source_name: str,
) -> DualSourceEvidence:
    """Require both activity and references evidence for both knowledge sources."""
    activities = _list(response, "activity", "activity_contents")
    references = _list(response, "references", "references_contents")
    activity_by_id: dict[str, dict[str, Any]] = {}
    activity_sources: dict[str, list[dict[str, Any]]] = {
        search_knowledge_source_name: [],
        mcp_knowledge_source_name: [],
    }

    for activity in activities:
        activity_id = _value(activity, "id")
        if activity_id is not None:
            activity_by_id[str(activity_id)] = activity
        source_name = _value(
            activity,
            "knowledgeSourceName",
            "knowledge_source_name",
        )
        if source_name in activity_sources:
            activity_sources[source_name].append(activity)

    reference_sources: dict[str, list[dict[str, Any]]] = {
        search_knowledge_source_name: [],
        mcp_knowledge_source_name: [],
    }
    for reference in references:
        source_name = _value(
            reference,
            "knowledgeSourceName",
            "knowledge_source_name",
        )
        if source_name not in reference_sources:
            activity_source = _value(
                reference,
                "activitySource",
                "activity_source",
            )
            linked_activity = activity_by_id.get(str(activity_source))
            if linked_activity:
                source_name = _value(
                    linked_activity,
                    "knowledgeSourceName",
                    "knowledge_source_name",
                )
        if source_name in reference_sources:
            reference_sources[source_name].append(reference)

    evidence = DualSourceEvidence(
        search=_source_evidence(
            search_knowledge_source_name,
            activity_sources,
            reference_sources,
        ),
        mcp=_source_evidence(
            mcp_knowledge_source_name,
            activity_sources,
            reference_sources,
        ),
    )
    if not evidence.both_participated:
        raise RuntimeError(
            "Cross-source verification failed. Expected at least one activity "
            "record and one linked reference from each knowledge source. "
            f"Observed: {evidence.as_dict()}"
        )
    return evidence


def _source_evidence(
    name: str,
    activity_sources: dict[str, list[dict[str, Any]]],
    reference_sources: dict[str, list[dict[str, Any]]],
) -> SourceEvidence:
    activities = activity_sources[name]
    references = reference_sources[name]
    return SourceEvidence(
        knowledge_source_name=name,
        activity_count=len(activities),
        reference_count=len(references),
        activity_types=tuple(
            sorted(
                {
                    str(_value(item, "type", "kind") or "unknown")
                    for item in activities
                }
            )
        ),
        reference_types=tuple(
            sorted(
                {
                    str(_value(item, "type", "kind") or "unknown")
                    for item in references
                }
            )
        ),
    )


def _list(response: dict[str, Any], *names: str) -> list[dict[str, Any]]:
    for name in names:
        value = response.get(name)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _value(item: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in item:
            return item[name]
    return None
