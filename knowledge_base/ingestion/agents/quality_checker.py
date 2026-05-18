from dataclasses import dataclass
from knowledge_base.models.entry import KnowledgeEntry


@dataclass
class ValidationReport:
    entry_id: str
    passed: bool
    issues: list[str]
    requires_review: bool


class QualityChecker:
    CONFIDENCE_THRESHOLD = 0.7

    def check(self, entry: KnowledgeEntry) -> ValidationReport:
        issues = []
        if not entry.title:
            issues.append("missing title")
        if not entry.summary:
            issues.append("missing summary")
        if entry.confidence_score < self.CONFIDENCE_THRESHOLD:
            issues.append(f"low confidence: {entry.confidence_score:.2f}")
        if not entry.structured_data:
            issues.append("empty structured_data")

        requires_review = len(issues) > 0 or entry.confidence_score < self.CONFIDENCE_THRESHOLD
        entry.requires_review = requires_review

        return ValidationReport(
            entry_id=entry.id,
            passed=len(issues) == 0,
            issues=issues,
            requires_review=requires_review,
        )
