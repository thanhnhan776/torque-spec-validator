"""Backward-compatible imports for address validators."""

from .address_dates import AddressDateValidator
from .address_fields import AddressFieldsValidator
from .duplicates import DuplicateRecordValidator, normalized_record
from .notes_dates import NotesDateValidator
from .overlaps import MAX_OVERLAP_FINDINGS, OverlappingTorqueSpecificationsValidator
from .utils import parsed_date
