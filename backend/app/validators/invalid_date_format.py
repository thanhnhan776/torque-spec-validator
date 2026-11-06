from ..parser import TorqueDocument
from .base import BaseValidator, ValidationResult, Severity
from .utils import validate_date_str


class InvalidDateFormatValidator(BaseValidator):

    @property
    def name(self) -> str:
        return "invalid_date_format"

    def validate(self, document: TorqueDocument) -> list[ValidationResult]:
        issues = []
        if document.document_date:
            error_msg = validate_date_str(document.document_date, 'DocumentDate')
            if error_msg:
                issues.append(
                    ValidationResult(
                        code=None,
                        severity=Severity.ERROR,
                        message=error_msg,
                        validator=self.name,
                    )
                )

        for address in document.addresses:
            fields = [
                {
                    "date_str": address.start_date,
                    "field_name": "StartDate",
                },
                {
                    "date_str": address.end_date,
                    "field_name": "EndDate",
                },
            ]
            for field in fields:
                if field["date_str"]:
                    start_date_error_msg = validate_date_str(field["date_str"], field["field_name"])
                    if start_date_error_msg:
                        issues.append(
                            ValidationResult(
                                code=address.code,
                                severity=Severity.ERROR,
                                message=start_date_error_msg,
                                validator=self.name
                            )
                        )
        return issues
