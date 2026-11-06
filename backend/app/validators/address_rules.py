from datetime import date

from ..parser import TorqueDocument
from .base import BaseValidator, Severity, ValidationResult
from .utils import parse_date_str


def parsed_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return parse_date_str(value).date()
    except ValueError:
        return None


class AddressFieldsValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "address_fields"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        for address in document.addresses:
            checks = (
                (not address.code, "missing_code", Severity.ERROR, "Missing Code value."),
                (
                    address.torque is not None and address.torque <= 0,
                    "non_possitive_torque",
                    Severity.ERROR,
                    "Torque must be positive.",
                ),
                (
                    not address.start_date,
                    "missing_start_date",
                    Severity.WARNING,
                    "Missing StartDate value.",
                ),
                (
                    not address.end_date,
                    "missing_end_date",
                    Severity.WARNING,
                    "Missing EndDate value.",
                ),
                (not address.notes, "missing_notes", Severity.INFO, "Missing Notes value."),
            )
            for failed, name, severity, message in checks:
                if failed:
                    issues.append(
                        ValidationResult(
                            code=address.code, severity=severity, message=message, validator=name
                        )
                    )
        return issues


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


class DuplicateRecordValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "duplicate_record"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        seen: set[tuple[str, float]] = set()
        for address in document.addresses:
            if not address.code or address.torque is None:
                continue
            key = (address.code, address.torque)
            if key in seen:
                issues.append(
                    ValidationResult(
                        code=address.code,
                        severity=Severity.WARNING,
                        message=f"Duplicate Code and Torque: {address.code!r}, {address.torque}.",
                        validator=self.name,
                    )
                )
            seen.add(key)
        return issues
