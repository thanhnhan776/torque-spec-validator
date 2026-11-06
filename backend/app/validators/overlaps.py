from datetime import date
import heapq

from ..parser import Address, TorqueDocument, exact_torque
from .base import BaseValidator, Severity, ValidationResult
from .utils import parsed_date

MAX_OVERLAP_FINDINGS = 1000


class OverlappingTorqueSpecificationsValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "overlapping_torque_specifications"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        groups: dict[str, list[tuple[date, date, int, Address]]] = {}
        for index, address in enumerate(document.addresses):
            code = address.code.strip()
            start = parsed_date(address.start_date)
            end = parsed_date(address.end_date)
            torque = exact_torque(address)
            if (
                not code
                or start is None
                or end is None
                or start > end
                or torque is None
                or torque <= 0
            ):
                continue
            groups.setdefault(code, []).append((start, end, index, address))

        for intervals in groups.values():
            active: dict[int, Address] = {}
            endings: list[tuple[date, int]] = []
            for start, end, index, address in sorted(intervals):
                while endings and endings[0][0] < start:
                    _, expired = heapq.heappop(endings)
                    del active[expired]
                for other in active.values():
                    if len(issues) == MAX_OVERLAP_FINDINGS:
                        issues.append(
                            ValidationResult(
                                severity=Severity.WARNING,
                                message=(
                                    "Overlap findings truncated after "
                                    f"{MAX_OVERLAP_FINDINGS} pairs; additional overlaps "
                                    "were not evaluated and may include errors."
                                ),
                                validator="overlapping_torque_specifications_truncated",
                            )
                        )
                        return issues
                    issues.append(
                        ValidationResult(
                            code=address.code,
                            severity=(
                                Severity.WARNING
                                if exact_torque(address) == exact_torque(other)
                                else Severity.ERROR
                            ),
                            message="Overlapping torque specifications for the same Code.",
                            validator=self.name,
                        )
                    )
                active[index] = address
                heapq.heappush(endings, (end, index))
        return issues
