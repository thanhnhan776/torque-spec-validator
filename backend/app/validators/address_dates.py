from datetime import date

from ..parser import TorqueDocument
from .base import BaseValidator, Severity, ValidationResult
from .utils import parsed_date


class AddressDateValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "address_dates"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        document_date = parsed_date(document.document_date)
        today = date.today()
        for address in document.addresses:
            start = parsed_date(address.start_date)
            end = parsed_date(address.end_date)
            checks = (
                (
                    start is not None and document_date is not None and start > document_date,
                    "start_date_after_document_date",
                    Severity.WARNING,
                    "StartDate is after DocumentDate.",
                ),
                (
                    start is not None and start > today,
                    "start_date_after_current_date",
                    Severity.WARNING,
                    "StartDate is after the current date.",
                ),
                (
                    end is not None and document_date is not None and end < document_date,
                    "end_date_before_document_date",
                    Severity.WARNING,
                    "EndDate is before DocumentDate.",
                ),
                (
                    end is not None and end < today,
                    "end_date_before_current_date",
                    Severity.WARNING,
                    "EndDate is before the current date.",
                ),
                (
                    start is not None and end is not None and start > end,
                    "invalid_date_range",
                    Severity.ERROR,
                    "StartDate is after EndDate.",
                ),
            )
            for failed, name, severity, message in checks:
                if failed:
                    issues.append(
                        ValidationResult(
                            code=address.code, severity=severity, message=message, validator=name
                        )
                    )
        return issues
