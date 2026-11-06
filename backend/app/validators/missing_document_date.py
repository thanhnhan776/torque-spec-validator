from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity


class MissingDocumentDateValidator(BaseValidator):

    @property
    def name(self) -> str:
        return "missing_document_date"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        if not document.document_date:
            issues.append(
                ValidationResult(
                    code=None,
                    severity=Severity.WARNING,
                    message="Missing DocumentDate value.",
                    validator=self.name,
                )
            )
        return issues
