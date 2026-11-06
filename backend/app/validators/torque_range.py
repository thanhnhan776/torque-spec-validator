from decimal import Decimal, InvalidOperation
import os

from ..parser import TorqueDocument, exact_torque
from .base import BaseValidator, Severity, ValidationResult


def configured_torque_range() -> tuple[Decimal, Decimal]:
    """Read the inclusive range, defaulting each unset bound independently."""
    minimum = os.environ.get("PLAUSIBLE_TORQUE_MIN", "0")
    maximum = os.environ.get("PLAUSIBLE_TORQUE_MAX", "1000")
    try:
        lower, upper = Decimal(minimum), Decimal(maximum)
    except InvalidOperation as exc:
        raise ValueError("Plausible torque bounds must be finite nonnegative numbers") from exc
    if not (lower.is_finite() and upper.is_finite() and 0 <= lower <= upper):
        raise ValueError("Plausible torque bounds must be finite, nonnegative and ordered")
    return lower, upper


class ImplausibleTorqueValidator(BaseValidator):
    def __init__(self, minimum: Decimal, maximum: Decimal) -> None:
        self.minimum = minimum
        self.maximum = maximum

    @property
    def name(self) -> str:
        return "implausible_torque"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        return [
            ValidationResult(
                code=address.code,
                severity=Severity.WARNING,
                message="Torque is outside the configured plausible range.",
                validator=self.name,
            )
            for address in document.addresses
            if (torque := exact_torque(address)) is not None
            and torque > 0
            and not self.minimum <= torque <= self.maximum
        ]
