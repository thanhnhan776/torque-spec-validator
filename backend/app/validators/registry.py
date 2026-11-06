from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult

# ──────────────────────────────────────────────────────────────
# Validator Registry
#
# Register your validators here. Each validator must subclass
# BaseValidator and implement validate().
#
# The example MissingTorqueValidator is provided to show the
# pattern. Add your own validators below.
# ──────────────────────────────────────────────────────────────

from .missing_torque import MissingTorqueValidator
from .missing_document_date import MissingDocumentDateValidator
from .invalid_date_format import InvalidDateFormatValidator
from .address_rules import AddressDateValidator, AddressFieldsValidator, DuplicateRecordValidator

VALIDATORS: list[BaseValidator] = [
    MissingTorqueValidator(),
    MissingDocumentDateValidator(),
    InvalidDateFormatValidator(),
    AddressFieldsValidator(),
    AddressDateValidator(),
    DuplicateRecordValidator(),
]


def run_all_validators(document: TorqueDocument) -> list[ValidationResult]:
    """Run all registered validators and collect results."""
    results = []
    for validator in VALIDATORS:
        results.extend(validator.validate(document))
    return results
