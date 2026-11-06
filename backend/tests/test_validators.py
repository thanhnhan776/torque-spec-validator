import unittest
import asyncio
import json
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import UploadFile
from fastapi.responses import JSONResponse

from app.main import app, upload_file
from app.parser import Address, TorqueDocument, parse_torque_xml
from app.validators.base import Severity
from app.validators.overlaps import OverlappingTorqueSpecificationsValidator
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
    @patch.dict("os.environ", {}, clear=True)
    def test_malformed_torque_multipart_upload_preserves_api_contract(self) -> None:
        xml = b"""<TorqueDocument><DocumentDate>2024-09-15</DocumentDate>
        <Address><Code>1AZ</Code><Torque>not-a-number</Torque><Notes>part</Notes>
        <StartDate>2020-01-01</StartDate><EndDate>2030-12-31</EndDate>
        </Address></TorqueDocument>"""
        body = (
            b'--test-boundary\r\nContent-Disposition: form-data; name="file"; '
            b'filename="test.xml"\r\nContent-Type: application/xml\r\n\r\n'
            + xml
            + b"\r\n--test-boundary--\r\n"
        )
        messages = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/upload",
            "raw_path": b"/api/upload",
            "query_string": b"",
            "headers": [
                (b"host", b"test"),
                (b"content-type", b"multipart/form-data; boundary=test-boundary"),
            ],
            "server": ("test", 80),
            "client": ("test", 1234),
            "root_path": "",
        }
        asyncio.run(app(scope, receive, send))
        self.assertEqual(messages[0]["status"], 200)
        response = json.loads(b"".join(message.get("body", b"") for message in messages[1:]))
        self.assertEqual(
            set(response),
            {
                "id",
                "uploaded_at",
                "filename",
                "document_date",
                "notes",
                "manufacturer",
                "series",
                "main_group",
                "sub_group",
                "addresses",
                "validations",
            },
        )
        self.assertEqual(
            set(response["addresses"][0]), {"code", "torque", "notes", "start_date", "end_date"}
        )
        self.assertIsNone(response["addresses"][0]["torque"])
        invalid = [
            finding
            for finding in response["validations"]
            if finding["validator"] == "invalid_torque_format"
        ]
        self.assertEqual(len(invalid), 1)
        self.assertEqual(set(invalid[0]), {"code", "severity", "message", "validator"})
        self.assertEqual((invalid[0]["code"], invalid[0]["severity"]), ("1AZ", "error"))

    def test_parser_preserves_torque_inputs_and_metadata(self) -> None:
        xml = b"""<TorqueDocument><Manufacturer>AZD</Manufacturer><Series>F01</Series>
        <MainGroup>41</MainGroup><SubGroup>61</SubGroup><Addresses>
        <Address><Torque>18,5</Torque></Address><Address/>
        <Address><Torque>abc</Torque></Address><Address><Torque>NaN</Torque></Address>
        <Address><Torque>1e999</Torque></Address></Addresses></TorqueDocument>"""
        doc = parse_torque_xml(xml, "test.xml")
        self.assertEqual(
            (doc.manufacturer, doc.series, doc.main_group, doc.sub_group),
            ("AZD", "F01", "41", "61"),
        )
        self.assertEqual([a.torque for a in doc.addresses], [18.5, None, None, None, None])
        self.assertEqual(
            [a.torque_raw for a in doc.addresses], ["18,5", None, "abc", "NaN", "1e999"]
        )

    def test_upload_returns_json_safe_torque_values(self) -> None:
        xml = b"""<TorqueDocument><Manufacturer>AZD</Manufacturer><Series>F01</Series>
        <MainGroup>41</MainGroup><SubGroup>61</SubGroup><Addresses>
        <Address><Torque>18,5</Torque></Address><Address/>
        <Address><Torque>abc</Torque></Address><Address><Torque>Infinity</Torque></Address>
        </Addresses></TorqueDocument>"""
        response = asyncio.run(upload_file(UploadFile(filename="test.xml", file=BytesIO(xml))))
        JSONResponse(response).render(response)
        self.assertEqual([a["torque"] for a in response["addresses"]], [18.5, None, None, None])
        self.assertEqual(
            [response[key] for key in ("manufacturer", "series", "main_group", "sub_group")],
            ["AZD", "F01", "41", "61"],
        )

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

    @patch("app.validators.address_dates.date", FixedDate)
    def test_torque_categories_from_xml_are_mutually_exclusive(self) -> None:
        cases = (
            (None, "missing_torque"),
            ("", "missing_torque"),
            ("   ", "missing_torque"),
            ("abc", "invalid_torque_format"),
            ("NaN", "invalid_torque_format"),
            ("Infinity", "invalid_torque_format"),
            ("-Infinity", "invalid_torque_format"),
            ("1e999", None),
            ("0", "non_possitive_torque"),
            ("-1,5", "non_possitive_torque"),
            ("1.5", None),
            ("1,5", None),
        )
        torque_rules = {"missing_torque", "invalid_torque_format", "non_possitive_torque"}
        for value, expected in cases:
            with self.subTest(value=value):
                torque = "" if value is None else f"<Torque>{value}</Torque>"
                xml = f"""<TorqueDocument><DocumentDate>2024-09-15</DocumentDate>
                <Address><Code>1AZ</Code>{torque}<Notes>note</Notes>
                <StartDate>2020-01-01</StartDate><EndDate>2030-12-31</EndDate>
                </Address></TorqueDocument>""".encode()
                result = findings(parse_torque_xml(xml, "test.xml"))
                actual = [item for item in result if item[0] in torque_rules]
                self.assertEqual(
                    actual, [] if expected is None else [(expected, Severity.ERROR, "1AZ")]
                )

    def test_direct_nonfinite_torque_is_invalid(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                result = findings(document(address(torque=value)))
                self.assertIn(("invalid_torque_format", Severity.ERROR, "1AZ"), result)
                self.assertNotIn(("non_possitive_torque", Severity.ERROR, "1AZ"), result)

    @patch.dict(
        "os.environ",
        {
            "PLAUSIBLE_TORQUE_MIN": "1.0000000000000000001",
            "PLAUSIBLE_TORQUE_MAX": "1.0000000000000000002",
        },
        clear=True,
    )
    def test_torque_comparisons_use_exact_source_and_bounds(self) -> None:
        xml = b"""<TorqueDocument><Address><Code>1AZ</Code><Torque>1.0000000000000000001</Torque>
        <StartDate>2020-01-01</StartDate><EndDate>2030-01-01</EndDate></Address>
        <Address><Code>1AZ</Code><Torque>1.0000000000000000002</Torque>
        <StartDate>2020-01-01</StartDate><EndDate>2030-01-01</EndDate></Address>
        <Address><Code>low</Code><Torque>1.0000000000000000000</Torque></Address>
        <Address><Code>high</Code><Torque>1.0000000000000000003</Torque></Address>
        </TorqueDocument>"""
        result = findings(parse_torque_xml(xml, "test.xml"))
        self.assertNotIn(("duplicate_record", Severity.WARNING, "1AZ"), result)
        self.assertIn(("overlapping_torque_specifications", Severity.ERROR, "1AZ"), result)
        self.assertEqual(
            [code for name, _, code in result if name == "implausible_torque"], ["low", "high"]
        )

    @patch.dict(
        "os.environ",
        {"PLAUSIBLE_TORQUE_MIN": "1e-999", "PLAUSIBLE_TORQUE_MAX": "1e999"},
        clear=True,
    )
    def test_extreme_finite_torque_uses_exact_values_despite_json_projection(self) -> None:
        xml = b"""<TorqueDocument><Address><Code>tiny</Code><Torque>1e-999</Torque></Address>
        <Address><Code>negative</Code><Torque>-1e-999</Torque></Address>
        <Address><Code>huge</Code><Torque>1e999</Torque></Address>
        <Address><Code>above</Code><Torque>1e1000</Torque></Address></TorqueDocument>"""
        doc = parse_torque_xml(xml, "test.xml")
        result = findings(doc)
        self.assertEqual([a.torque for a in doc.addresses], [0.0, -0.0, None, None])
        self.assertIn(("non_possitive_torque", Severity.ERROR, "negative"), result)
        self.assertNotIn(("non_possitive_torque", Severity.ERROR, "tiny"), result)
        self.assertFalse(any(name == "invalid_torque_format" for name, _, _ in result))
        self.assertEqual(
            [code for name, _, code in result if name == "implausible_torque"], ["above"]
        )
        response = asyncio.run(upload_file(UploadFile(filename="test.xml", file=BytesIO(xml))))
        JSONResponse(response).render(response)
        self.assertEqual([a["torque"] for a in response["addresses"]], [0.0, -0.0, None, None])

    @patch.dict("os.environ", {}, clear=True)
    def test_default_plausible_torque_range(self) -> None:
        doc = document(
            address(code="zero", torque=0),
            address(code="negative", torque=-1),
            address(code="small", torque=0.0001),
            address(code="max", torque=1000),
            address(code="high", torque=1000.1),
        )
        result = findings(doc)
        self.assertEqual(
            [code for name, _, code in result if name == "implausible_torque"], ["high"]
        )
        self.assertIn(("non_possitive_torque", Severity.ERROR, "zero"), result)
        self.assertIn(("non_possitive_torque", Severity.ERROR, "negative"), result)

    def test_individually_defaulted_torque_bounds(self) -> None:
        cases = (
            ({"PLAUSIBLE_TORQUE_MIN": "10"}, ["low", "high"]),
            ({"PLAUSIBLE_TORQUE_MAX": "20"}, ["high"]),
            ({"PLAUSIBLE_TORQUE_MIN": "0", "PLAUSIBLE_TORQUE_MAX": "0"}, ["low", "high"]),
        )
        for config, expected in cases:
            with self.subTest(config=config), patch.dict("os.environ", config, clear=True):
                result = findings(
                    document(address(code="low", torque=5), address(code="high", torque=1001))
                )
                self.assertEqual(
                    [code for name, _, code in result if name == "implausible_torque"], expected
                )

    @patch.dict(
        "os.environ", {"PLAUSIBLE_TORQUE_MIN": "10", "PLAUSIBLE_TORQUE_MAX": "20"}, clear=True
    )
    def test_plausible_torque_range_and_boundaries(self) -> None:
        xml = b"""<TorqueDocument><Address><Code>low</Code><Torque>9,5</Torque></Address>
        <Address><Code>min</Code><Torque>10</Torque></Address>
        <Address><Code>max</Code><Torque>20</Torque></Address>
        <Address><Code>high</Code><Torque>20,5</Torque></Address>
        <Address><Code>invalid</Code><Torque>NaN</Torque></Address>
        <Address><Code>zero</Code><Torque>0</Torque></Address></TorqueDocument>"""
        doc = parse_torque_xml(xml, "test.xml")
        before = [(item.torque, item.torque_raw) for item in doc.addresses]
        result = [item for item in findings(doc) if item[0] == "implausible_torque"]
        self.assertEqual(
            result,
            [
                ("implausible_torque", Severity.WARNING, "low"),
                ("implausible_torque", Severity.WARNING, "high"),
            ],
        )
        self.assertEqual([(item.torque, item.torque_raw) for item in doc.addresses], before)

    def test_invalid_plausible_torque_configuration(self) -> None:
        cases = (
            {"PLAUSIBLE_TORQUE_MIN": "", "PLAUSIBLE_TORQUE_MAX": "2"},
            {"PLAUSIBLE_TORQUE_MIN": "nan", "PLAUSIBLE_TORQUE_MAX": "2"},
            {"PLAUSIBLE_TORQUE_MIN": "1", "PLAUSIBLE_TORQUE_MAX": "inf"},
            {"PLAUSIBLE_TORQUE_MIN": "-1"},
            {"PLAUSIBLE_TORQUE_MAX": "-1"},
            {"PLAUSIBLE_TORQUE_MIN": "1001"},
            {"PLAUSIBLE_TORQUE_MIN": "3", "PLAUSIBLE_TORQUE_MAX": "2"},
        )
        for config in cases:
            with self.subTest(config=config), patch.dict("os.environ", config, clear=True):
                with self.assertRaises(ValueError):
                    run_all_validators(document(address()))

    def test_strict_date_format_for_every_field(self) -> None:
        for invalid in ("2024-1-01", "2024-01-1", "2024-02-30", "2024-01-01T00:00:00"):
            with self.subTest(invalid=invalid):
                result = findings(
                    document(address(start_date=invalid, end_date=invalid), document_date=invalid)
                )
                self.assertEqual(result.count(("invalid_date_format", Severity.ERROR, None)), 1)
                self.assertEqual(result.count(("invalid_date_format", Severity.ERROR, "1AZ")), 2)
                self.assertEqual(len(result), 3)

    @patch("app.validators.address_dates.date", FixedDate)
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

    @patch("app.validators.address_dates.date", FixedDate)
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

    def test_duplicates_compare_all_normalized_fields(self) -> None:
        doc = document(
            address(),
            address(code=" 1AZ ", notes=" Bonnet to hinge "),
            address(notes="different"),
            address(start_date="2021-01-01"),
            address(end_date="2029-01-01"),
            address(torque=28),
            address(code="2AZ"),
        )
        duplicates = [item for item in findings(doc) if item[0] == "duplicate_record"]
        self.assertEqual(duplicates, [("duplicate_record", Severity.WARNING, " 1AZ ")])

    def test_duplicate_normalizes_torque_but_preserves_invalid_input(self) -> None:
        xml = b"""<TorqueDocument><Address><Code>1AZ</Code><Torque>18,5</Torque></Address>
        <Address><Code>1AZ</Code><Torque>18.5</Torque></Address>
        <Address><Code>1AZ</Code><Torque>bad</Torque></Address>
        <Address><Code>1AZ</Code><Torque>other</Torque></Address></TorqueDocument>"""
        duplicates = [
            item
            for item in findings(parse_torque_xml(xml, "test.xml"))
            if item[0] == "duplicate_record"
        ]
        self.assertEqual(duplicates, [("duplicate_record", Severity.WARNING, "1AZ")])

    def test_overlap_severity_and_inclusive_endpoints(self) -> None:
        cases = (
            ("2025-01-01", 20, Severity.WARNING),
            ("2025-01-01", 30, Severity.ERROR),
            ("2024-06-01", 30, Severity.ERROR),
            ("2025-01-02", 30, None),
        )
        for start, torque, expected in cases:
            with self.subTest(start=start, torque=torque):
                doc = document(
                    address(end_date="2025-01-01"), address(start_date=start, torque=torque)
                )
                overlaps = [
                    item for item in findings(doc) if item[0] == "overlapping_torque_specifications"
                ]
                self.assertEqual(
                    overlaps,
                    (
                        []
                        if expected is None
                        else [("overlapping_torque_specifications", expected, "1AZ")]
                    ),
                )

    def test_overlap_excludes_invalid_inputs_and_other_codes(self) -> None:
        cases = (
            {"start_date": None},
            {"end_date": "2024-02-30"},
            {"start_date": "2031-01-01"},
            {"torque": None, "torque_raw": "bad"},
            {"torque": float("nan")},
            {"torque": 0},
            {"torque": -1},
            {"code": "2AZ"},
            {"code": ""},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                overlaps = [
                    item
                    for item in findings(document(address(), address(**changes)))
                    if item[0] == "overlapping_torque_specifications"
                ]
                self.assertEqual(overlaps, [])

    def test_overlap_many_disjoint_ranges_and_late_conflict(self) -> None:
        start = date(2000, 1, 1)
        entries = [
            address(
                start_date=(start + timedelta(days=2 * i)).isoformat(),
                end_date=(start + timedelta(days=2 * i)).isoformat(),
            )
            for i in range(5000)
        ]
        entries.append(
            address(start_date=entries[-1].start_date, end_date=entries[-1].end_date, torque=30)
        )
        result = OverlappingTorqueSpecificationsValidator().validate(document(*entries))
        self.assertEqual(
            [(item.severity, item.validator) for item in result],
            [(Severity.ERROR, "overlapping_torque_specifications")],
        )

    @patch("app.validators.overlaps.MAX_OVERLAP_FINDINGS", 2)
    def test_overlap_limit_warns_only_when_additional_pair_exists(self) -> None:
        validator = OverlappingTorqueSpecificationsValidator()
        exact = document(
            address(), address(), address(start_date="2030-12-31", end_date="2030-12-31")
        )
        # Three overlapping pairs exceed the cap.
        truncated = validator.validate(exact)
        self.assertEqual(len(truncated), 3)
        self.assertEqual(truncated[-1].validator, "overlapping_torque_specifications_truncated")
        self.assertEqual(truncated[-1].severity, Severity.WARNING)
        self.assertIn("may include errors", truncated[-1].message)

    @patch("app.validators.overlaps.MAX_OVERLAP_FINDINGS", 2)
    def test_overlap_limit_exactly_reached_has_no_truncation_warning(self) -> None:
        doc = document(address(code="a"), address(code="a"), address(code="b"), address(code="b"))
        result = OverlappingTorqueSpecificationsValidator().validate(doc)
        self.assertEqual(len(result), 2)
        self.assertTrue(
            all(item.validator == "overlapping_torque_specifications" for item in result)
        )

    def test_notes_date_boundaries(self) -> None:
        cases = (
            ("Part, from 01/2020", False),
            ("Part, to 12/2030", False),
            ("Part, from 02/2020", True),
            ("Part, to 11/2030", True),
            ("Part, from 01/2021, to 12/2030", True),
            ("Part, from 13/2020", False),
            ("Part, to 00/2030", False),
            ("Part, from 01/0000", False),
            ("Part, approximately from 02/2020", False),
            ("Part, from 02/2020 or 03/2020", False),
            ("Part, from 02/2020, from 03/2020", False),
            ("Part, from 02/2020/01", False),
        )
        for notes, expected in cases:
            with self.subTest(notes=notes):
                result = [
                    item
                    for item in findings(document(address(notes=notes)))
                    if item[0] == "notes_date_mismatch"
                ]
                self.assertEqual(
                    result, [("notes_date_mismatch", Severity.WARNING, "1AZ")] if expected else []
                )

    def test_notes_date_skips_invalid_ranges(self) -> None:
        for changes in (
            {"start_date": None},
            {"end_date": "2020-02-30"},
            {"start_date": "2031-01-01"},
        ):
            with self.subTest(changes=changes):
                result = findings(document(address(notes="Part, from 02/2020", **changes)))
                self.assertFalse(any(item[0] == "notes_date_mismatch" for item in result))

    def test_notes_iso_date_boundaries_and_ambiguity(self) -> None:
        cases = (
            ("from 2020-01-01", False),
            ("Part, TO 2030-12-31.", False),
            ("Part, from 2020-01-02", True),
            ("Part, to 2030-12-30", True),
            ("Part, from 2020-01-01; to 2030-12-30", True),
            ("Part, from 01/2020; to 2030-12-31", False),
            ("Part, from 2020-01-02; from 01/2020", False),
            ("Part, from 2020-02-30", False),
            ("Part, from 0000-01-01", False),
            ("Part, from 2020-1-02", False),
            ("Part, from 2020-01-02T00:00:00", False),
            ("Part, from 2020-01-02/03", False),
            ("Part, approximately from 2020-01-02", False),
            ("Part, from 2020-01-02 or 2020-01-03", False),
        )
        for notes, expected in cases:
            with self.subTest(notes=notes):
                result = [
                    item
                    for item in findings(document(address(notes=notes)))
                    if item[0] == "notes_date_mismatch"
                ]
                self.assertEqual(
                    result, [("notes_date_mismatch", Severity.WARNING, "1AZ")] if expected else []
                )

    def test_notes_iso_leap_day_and_invalid_address_range(self) -> None:
        matching = address(start_date="2020-02-29", notes="from 2020-02-29")
        mismatch = address(start_date="2020-02-28", notes="from 2020-02-29")
        invalid = address(start_date="2020-02-30", notes="from 2020-02-29")
        for entry, expected in ((matching, False), (mismatch, True), (invalid, False)):
            with self.subTest(entry=entry):
                result = [
                    item for item in findings(document(entry)) if item[0] == "notes_date_mismatch"
                ]
                self.assertEqual(bool(result), expected)

    def test_filename_metadata_matching_and_each_mismatch(self) -> None:
        path = Path(__file__).resolve().parents[2] / "data/AZD-AZD-AZDMUC4161-F01_RBU.xml"
        doc = parse_torque_xml(path.read_bytes(), path.name)
        self.assertFalse(any(item[0] == "filename_metadata_mismatch" for item in findings(doc)))
        for field in ("manufacturer", "series", "main_group", "sub_group"):
            with self.subTest(field=field):
                changed = parse_torque_xml(path.read_bytes(), path.name)
                setattr(changed, field, "different")
                self.assertIn(
                    ("filename_metadata_mismatch", Severity.WARNING, None), findings(changed)
                )

    def test_filename_unparseable_and_missing_metadata_are_skipped(self) -> None:
        for filename in (
            "test.xml",
            "AZD-OTHER-AZDMUC4161-F01_RBU.xml",
            "AZD-AZD-AZDMUC416-F01_RBU.xml",
        ):
            with self.subTest(filename=filename):
                doc = TorqueDocument(filename, None, None, [address()], manufacturer="different")
                self.assertFalse(
                    any(item[0] == "filename_metadata_mismatch" for item in findings(doc))
                )
        doc = TorqueDocument("AZD-AZD-AZDMUC4161-F01_RBU.xml", None, None, [address()])
        self.assertFalse(any(item[0] == "filename_metadata_mismatch" for item in findings(doc)))
        doc.manufacturer = "AZD"
        doc.series = "different"
        self.assertIn(("filename_metadata_mismatch", Severity.WARNING, None), findings(doc))

    def test_empty_addresses_warning(self) -> None:
        self.assertIn(("empty_addresses", Severity.WARNING, None), findings(document()))
        self.assertNotIn(("empty_addresses", Severity.WARNING, None), findings(document(address())))

    @patch("app.validators.address_dates.date", FixedDate)
    def test_sample_xml_integration(self) -> None:
        path = Path(__file__).resolve().parents[2] / "data/AZD-AZD-AZDMUC4161-F01_RBU.xml"
        doc = parse_torque_xml(path.read_bytes(), path.name)
        result = findings(doc)
        self.assertIn(("end_date_before_document_date", Severity.WARNING, "3AZ"), result)
        self.assertNotIn(("duplicate_record", Severity.WARNING, "3AZ"), result)
        for item in doc.addresses:
            if item.notes and ("to 09/2010" in item.notes or "from 10/2010" in item.notes):
                self.assertFalse(
                    any(
                        f.validator == "notes_date_mismatch"
                        for f in run_all_validators(document(item))
                    )
                )


if __name__ == "__main__":
    unittest.main()
