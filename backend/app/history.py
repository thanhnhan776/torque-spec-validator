"""SQLite storage for completed upload snapshots, never source XML."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3


def connect() -> sqlite3.Connection:
    path = Path(os.environ.get("UPLOAD_HISTORY_DB", "upload_history.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS uploads "
        "(id TEXT PRIMARY KEY, uploaded_at TEXT NOT NULL, snapshot TEXT NOT NULL)"
    )
    return connection


def save_snapshot(snapshot: dict) -> None:
    serialized = json.dumps(snapshot, allow_nan=False)
    with closing(connect()) as connection, connection:
        connection.execute(
            "INSERT INTO uploads (id, uploaded_at, snapshot) VALUES (?, ?, ?)",
            (snapshot["id"], snapshot["uploaded_at"], serialized),
        )


def list_snapshots() -> list[dict]:
    with closing(connect()) as connection:
        rows = connection.execute(
            "SELECT snapshot FROM uploads ORDER BY uploaded_at DESC, rowid DESC"
        ).fetchall()
    summaries = []
    for (serialized,) in rows:
        snapshot = json.loads(serialized)
        counts = {severity: 0 for severity in ("error", "warning", "info")}
        for finding in snapshot["validations"]:
            counts[finding["severity"]] += 1
        summaries.append(
            {
                "id": snapshot["id"],
                "uploaded_at": snapshot["uploaded_at"],
                "filename": snapshot["filename"],
                "counts": counts,
            }
        )
    return summaries


def get_snapshot(upload_id: str) -> dict | None:
    with closing(connect()) as connection:
        row = connection.execute(
            "SELECT snapshot FROM uploads WHERE id = ?", (upload_id,)
        ).fetchone()
    return json.loads(row[0]) if row else None
