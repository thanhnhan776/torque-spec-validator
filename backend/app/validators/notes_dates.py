import re

from ..parser import TorqueDocument
from .base import BaseValidator, Severity, ValidationResult
from .utils import parsed_date

# Only standalone, explicitly directed date clauses are interpreted.
_NOTES_BOUNDARY = re.compile(
    r"(?:^|[,;(\n])\s*(from|to)\s+(?:(\d{1,2})/(\d{4})|([0-9]{4}-[0-9]{2}-[0-9]{2}))"
    r"(?=\s*(?:$|[,;).\n]))",
    re.IGNORECASE,
)


class NotesDateValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "notes_date_mismatch"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        for address in document.addresses:
            start = parsed_date(address.start_date)
            end = parsed_date(address.end_date)
            if start is None or end is None or start > end or not address.notes:
                continue
            boundaries: dict[str, list[tuple[int, ...]]] = {"from": [], "to": []}
            for match in _NOTES_BOUNDARY.finditer(address.notes):
                direction, month_text, year_text, iso_text = match.groups()
                if iso_text:
                    value = parsed_date(iso_text)
                    if value is None:
                        continue
                    boundary = (value.year, value.month, value.day)
                else:
                    month, year = int(month_text), int(year_text)
                    if not 1 <= month <= 12 or year == 0:
                        continue
                    boundary = (year, month)
                boundaries[direction.lower()].append(boundary)
            # Multiple alternative boundaries are ambiguous, even if one matches.
            if any(len(values) > 1 for values in boundaries.values()):
                continue
            mismatch = any(
                values and values[0] != (actual.year, actual.month, actual.day)[: len(values[0])]
                for values, actual in ((boundaries["from"], start), (boundaries["to"], end))
            )
            if mismatch:
                issues.append(
                    ValidationResult(
                        code=address.code,
                        severity=Severity.WARNING,
                        message="Notes date boundary differs from the address date range.",
                        validator=self.name,
                    )
                )
        return issues
