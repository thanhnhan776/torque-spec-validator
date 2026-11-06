# Validation rules

## Interested data fields
- DocumentDate
- Address.Code
- Address.Torque
- Address.StartDate
- Address.EndDate
- Address.Notes

## Fields validation

### 1. DocumentDate
- Required -> `missing_document_date`, WARNING
- Date format "YYYY-MM-DD" -> `invalid_date_format`, ERROR

### 2. Address.Code
- Required -> `missing_code`, ERROR

### 3. Address.Torque
- Required -> `missing_torque`, ERROR
- Numeric and finite (decimal comma accepted) -> `invalid_torque_format`, ERROR
- Possitive number ( > 0) -> `non_possitive_torque`, ERROR

### 4. Address.StartDate
- Required -> `missing_start_date`, WARNING
- Date format "YYYY-MM-DD" -> `invalid_date_format`, ERROR
- Start date is after Document date -> `start_date_after_document_date`, WARNING
- Start date is after Current date -> `start_date_after_current_date`, WARNING

### 5. Address.EndDate
- Required -> `missing_end_date`, WARNING
- Date format "YYYY-MM-DD" -> `invalid_date_format`, ERROR
- End date is before Document date -> `end_date_before_document_date`, WARNING
- End date is before Current date -> `end_date_before_current_date`, WARNING

### 6. Date range
- Start date > End date -> `invalid_date_range`, ERROR

### 7. Address.Notes
- Required -> `missing_notes`, INFO

### 8. Duplicate records
- Identical normalized records -> `duplicate_record`, WARNING

### 9. Overlapping specifications
- Same Code, overlapping inclusive dates, different torque -> `overlapping_torque_specifications`, ERROR
- Same Code and torque with overlapping dates -> `overlapping_torque_specifications`, WARNING
- Check valid dates and torque only; Notes may explain an overlap.
- Report at most 1,000 pairs; `overlapping_torque_specifications_truncated` warns if
  further pairs (including potential errors) are unevaluated. Order: code encounter,
  then ascending start date.

### 10. Implausible torque
- Finite positive torque outside the inclusive range -> `implausible_torque`, WARNING;
  non-positive torque remains an error. Values are not corrected.
- Bounds default independently to 0 and 1000 Nm. Override with backend environment
  variables `PLAUSIBLE_TORQUE_MIN` and `PLAUSIBLE_TORQUE_MAX` (decimal points).
  Bounds must be finite, nonnegative and ordered; invalid configuration raises an error.

### 11. Notes and dates
- Unambiguous date in Notes contradicts the date range -> `notes_date_mismatch`, WARNING (heuristic)

### 12. Filename and metadata
- Parsed filename metadata differs from XML metadata -> `filename_metadata_mismatch`, WARNING

### 13. Addresses
- No Address entries -> `empty_addresses`, WARNING
