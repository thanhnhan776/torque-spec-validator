from ..parser import Address, TorqueDocument, exact_torque
from .base import BaseValidator, Severity, ValidationResult


class DuplicateRecordValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "duplicate_record"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        seen: set[tuple[object, ...]] = set()
        for address in document.addresses:
            key = normalized_record(address)
            if key in seen:
                issues.append(
                    ValidationResult(
                        code=address.code,
                        severity=Severity.WARNING,
                        message="Duplicate normalized address record.",
                        validator=self.name,
                    )
                )
            seen.add(key)
        return issues


def normalized_record(address: Address) -> tuple[object, ...]:
    def text(value: str | None) -> str:
        return value.strip() if value else ""

    torque: object = exact_torque(address)
    if torque is None:
        torque = ("invalid_or_missing", text(address.torque_raw) or str(address.torque))
    return (
        text(address.code),
        torque,
        text(address.notes),
        text(address.start_date),
        text(address.end_date),
    )
