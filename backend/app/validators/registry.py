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

from .missing_document_date import MissingDocumentDateValidator
from .invalid_date_format import InvalidDateFormatValidator
from .address_dates import AddressDateValidator
from .address_fields import AddressFieldsValidator
from .duplicates import DuplicateRecordValidator
from .notes_dates import NotesDateValidator
from .overlaps import OverlappingTorqueSpecificationsValidator
from .document_rules import DocumentMetadataValidator, EmptyAddressesValidator
from .torque_range import ImplausibleTorqueValidator, configured_torque_range

VALIDATORS: list[BaseValidator] = [
    MissingDocumentDateValidator(),
    InvalidDateFormatValidator(),
    AddressFieldsValidator(),
    AddressDateValidator(),
    DuplicateRecordValidator(),
    OverlappingTorqueSpecificationsValidator(),
    NotesDateValidator(),
    DocumentMetadataValidator(),
    EmptyAddressesValidator(),
]


def run_all_validators(document: TorqueDocument) -> list[ValidationResult]:
    """Run all registered validators and collect results."""
    torque_range = configured_torque_range()
    results = []
    for validator in VALIDATORS:
        results.extend(validator.validate(document))
    if torque_range is not None:
        results.extend(ImplausibleTorqueValidator(*torque_range).validate(document))
    return results
