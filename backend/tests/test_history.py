import asyncio
from datetime import datetime, timezone
from io import BytesIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException, UploadFile

from app.main import get_upload, list_uploads, upload_file


class HistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(
            os.environ, {"UPLOAD_HISTORY_DB": str(Path(self.directory.name) / "history.sqlite3")}
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def upload(self, filename: str, content: bytes) -> dict:
        return asyncio.run(upload_file(UploadFile(filename=filename, file=BytesIO(content))))

    def test_snapshots_survive_new_connections_and_match_upload(self) -> None:
        first = self.upload("first.xml", b"<TorqueDocument/>")
        second = self.upload("second.xml", b"<TorqueDocument><Address/></TorqueDocument>")
        UUID(first["id"])
        self.assertEqual(
            datetime.fromisoformat(first["uploaded_at"]).utcoffset(), timezone.utc.utcoffset(None)
        )
        summaries = list_uploads()
        self.assertEqual([entry["id"] for entry in summaries], [second["id"], first["id"]])
        self.assertEqual(get_upload(first["id"]), first)
        self.assertEqual(get_upload(second["id"]), second)
        self.assertEqual(
            summaries[0]["counts"],
            {
                severity: sum(v["severity"] == severity for v in second["validations"])
                for severity in ("error", "warning", "info")
            },
        )
        self.assertNotIn(b"<TorqueDocument", Path(os.environ["UPLOAD_HISTORY_DB"]).read_bytes())

    def test_failures_do_not_create_history(self) -> None:
        for filename, content in (("bad.txt", b"x"), ("bad.xml", b"<broken")):
            with self.subTest(filename=filename), self.assertRaises(HTTPException):
                self.upload(filename, content)
        with patch("app.main.run_all_validators", side_effect=ValueError("failure")):
            with self.assertRaises(ValueError):
                self.upload("bad.xml", b"<TorqueDocument/>")
        self.assertEqual(list_uploads(), [])

    def test_unknown_upload_is_404(self) -> None:
        with self.assertRaises(HTTPException) as error:
            get_upload("unknown")
        self.assertEqual(error.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
