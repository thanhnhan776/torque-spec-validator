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

### 8. Unique together
- (Code, Torque) are unique together -> `duplicate_record`, WARNING