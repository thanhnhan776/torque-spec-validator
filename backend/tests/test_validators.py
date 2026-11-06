import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app.parser import Address, TorqueDocument, parse_torque_xml
from app.validators.base import Severity
from app.validators.registry import run_all_validators


def document(*addresses: Address, document_date: str | None = "2024-09-15") -> TorqueDocument:
    return TorqueDocument("test.xml", document_date, None, list(addresses))


def address(**changes: object) -> Address:
    values = {
        "code": "1AZ",
        "torque": 20.0,
        "notes": "Bonnet to hinge",
        "start_date": "2020-01-01",
        "end_date": "2030-12-31",
    }
    values.update(changes)
    return Address(**values)


def findings(doc: TorqueDocument) -> list[tuple[str, Severity, str | None]]:
    return [(result.validator, result.severity, result.code) for result in run_all_validators(doc)]


class FixedDate(date):
    @classmethod
    def today(cls) -> date:
        return cls(2025, 1, 1)


class ValidatorTests(unittest.TestCase):
    def test_required_fields_and_torque(self) -> None:
        doc = document(
            address(code="", torque=0, notes=None, start_date=None, end_date=None),
            document_date=None,
        )
        self.assertCountEqual(
            findings(doc),
            [
                ("missing_document_date", Severity.WARNING, None),
                ("missing_code", Severity.ERROR, ""),
                ("non_possitive_torque", Severity.ERROR, ""),
                ("missing_start_date", Severity.WARNING, ""),
                ("missing_end_date", Severity.WARNING, ""),
                ("missing_notes", Severity.INFO, ""),
            ],
        )
        self.assertIn(
            ("missing_torque", Severity.ERROR, "1AZ"), findings(document(address(torque=None)))
        )
        self.assertIn(
            ("non_possitive_torque", Severity.ERROR, "1AZ"), findings(document(address(torque=-1)))
        )

    def test_strict_date_format_for_every_field(self) -> None:
        for invalid in ("2024-1-01", "2024-01-1", "2024-02-30", "2024-01-01T00:00:00"):
            with self.subTest(invalid=invalid):
                result = findings(
                    document(address(start_date=invalid, end_date=invalid), document_date=invalid)
                )
                self.assertEqual(result.count(("invalid_date_format", Severity.ERROR, None)), 1)
                self.assertEqual(result.count(("invalid_date_format", Severity.ERROR, "1AZ")), 2)
                self.assertEqual(len(result), 3)

    @patch("app.validators.address_rules.date", FixedDate)
    def test_date_comparisons_and_equal_boundaries(self) -> None:
        result = findings(document(address(start_date="2025-01-02", end_date="2024-09-14")))
        self.assertCountEqual(
            result,
            [
                ("start_date_after_document_date", Severity.WARNING, "1AZ"),
                ("start_date_after_current_date", Severity.WARNING, "1AZ"),
                ("end_date_before_document_date", Severity.WARNING, "1AZ"),
                ("end_date_before_current_date", Severity.WARNING, "1AZ"),
                ("invalid_date_range", Severity.ERROR, "1AZ"),
            ],
        )
        self.assertEqual(
            findings(
                document(
                    address(start_date="2025-01-01", end_date="2025-01-01"),
                    document_date="2025-01-01",
                )
            ),
            [],
        )

    @patch("app.validators.address_rules.date", FixedDate)
    def test_invalid_or_missing_comparison_inputs_are_skipped(self) -> None:
        for value in (None, "2024-1-01", "2024-02-30"):
            with self.subTest(value=value):
                result = findings(
                    document(address(start_date=value, end_date=value), document_date=value)
                )
                self.assertFalse(
                    any(
                        name
                        in {
                            "start_date_after_document_date",
                            "start_date_after_current_date",
                            "end_date_before_document_date",
                            "end_date_before_current_date",
                            "invalid_date_range",
                        }
                        for name, _, _ in result
                    )
                )

    def test_duplicates_compare_code_and_torque_and_skip_missing(self) -> None:
        doc = document(
            address(),
            address(),
            address(torque=28),
            address(code="2AZ"),
            address(code="", torque=None),
            address(code="", torque=None),
        )
        duplicates = [item for item in findings(doc) if item[0] == "duplicate_record"]
        self.assertEqual(duplicates, [("duplicate_record", Severity.WARNING, "1AZ")])

    @patch("app.validators.address_rules.date", FixedDate)
    def test_sample_xml_integration(self) -> None:
        path = Path(__file__).resolve().parents[2] / "data/AZD-AZD-AZDMUC4161-F01_RBU.xml"
        doc = parse_torque_xml(path.read_bytes(), path.name)
        result = findings(doc)
        self.assertIn(("end_date_before_document_date", Severity.WARNING, "3AZ"), result)
        self.assertNotIn(("duplicate_record", Severity.WARNING, "3AZ"), result)


if __name__ == "__main__":
    unittest.main()
