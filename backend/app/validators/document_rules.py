import re

from ..parser import TorqueDocument
from .base import BaseValidator, Severity, ValidationResult

_FILENAME_PATTERN = re.compile(
    r"(?P<manufacturer>[A-Za-z0-9]+)-(?P=manufacturer)-"
    r"[A-Za-z]+(?P<main_group>[0-9]{2})(?P<sub_group>[0-9]{2})-"
    r"(?P<series>[A-Za-z0-9]+)_[A-Za-z0-9]+\.xml",
    re.IGNORECASE,
)


class DocumentMetadataValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "filename_metadata_mismatch"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        match = _FILENAME_PATTERN.fullmatch(document.filename)
        if not match:
            return []
        mismatches = [
            field
            for field in ("manufacturer", "series", "main_group", "sub_group")
            if (value := getattr(document, field))
            and value.strip()
            and value.strip().casefold() != match.group(field).casefold()
        ]
        if not mismatches:
            return []
        return [
            ValidationResult(
                severity=Severity.WARNING,
                message=f"Filename metadata differs from XML: {', '.join(mismatches)}.",
                validator=self.name,
            )
        ]


class EmptyAddressesValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "empty_addresses"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        if document.addresses:
            return []
        return [
            ValidationResult(
                severity=Severity.WARNING,
                message="Document contains no address entries.",
                validator=self.name,
            )
        ]
