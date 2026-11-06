from ..parser import TorqueDocument, exact_torque
from .base import BaseValidator, Severity, ValidationResult


class AddressFieldsValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "address_fields"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        for address in document.addresses:
            torque = exact_torque(address)
            checks = (
                (not address.code, "missing_code", Severity.ERROR, "Missing Code value."),
                (
                    address.torque is None and not address.torque_raw,
                    "missing_torque",
                    Severity.ERROR,
                    "Missing Torque value.",
                ),
                (
                    torque is None and (address.torque is not None or bool(address.torque_raw)),
                    "invalid_torque_format",
                    Severity.ERROR,
                    "Torque must be a finite number.",
                ),
                (
                    torque is not None and torque <= 0,
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
