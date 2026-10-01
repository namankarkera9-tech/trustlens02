"""Minimal SQLite persistence for analysis jobs and normalized result records."""

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


_LOCK = threading.RLock()
_DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "trustlens.sqlite3"


def database_path() -> Path:
    raw_path = os.getenv("DATABASE_PATH", str(_DEFAULT_DB))
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(str(database_path()), timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def initialize_database() -> None:
    with _LOCK, _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                error TEXT,
                result_json TEXT
            );
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
                source TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                category TEXT NOT NULL,
                timestamp REAL,
                record_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_evidence_analysis ON evidence(analysis_id);
            """
        )


def create_analysis(analysis_id: str, filename: str, content_type: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _LOCK, _connect() as connection:
        connection.execute(
            "INSERT INTO analyses(id,status,stage,progress,filename,content_type,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (analysis_id, "queued", "queued", 0, filename, content_type, now, now),
        )


def update_analysis(
    analysis_id: str,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    progress: Optional[int] = None,
    error: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
) -> bool:
    assignments = ["updated_at = ?"]
    values = [datetime.now(timezone.utc).isoformat()]
    for column, value in (("status", status), ("stage", stage), ("progress", progress), ("error", error)):
        if value is not None:
            assignments.append("{} = ?".format(column))
            values.append(value)
    if result is not None:
        assignments.append("result_json = ?")
        values.append(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    values.append(analysis_id)
    with _LOCK, _connect() as connection:
        cursor = connection.execute(
            "UPDATE analyses SET {} WHERE id = ?".format(", ".join(assignments)), values
        )
        return cursor.rowcount > 0


def replace_evidence(analysis_id: str, records: list) -> None:
    rows = []
    for record in records:
        data = record if isinstance(record, dict) else record.dict()
        rows.append(
            (
                data["id"],
                analysis_id,
                data["source"],
                data["type"],
                data["category"],
                data.get("timestamp"),
                json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            )
        )
    with _LOCK, _connect() as connection:
        connection.execute("DELETE FROM evidence WHERE analysis_id = ?", (analysis_id,))
        connection.executemany(
            "INSERT INTO evidence(id,analysis_id,source,evidence_type,category,timestamp,record_json) VALUES(?,?,?,?,?,?,?)",
            rows,
        )


def get_analysis(analysis_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK, _connect() as connection:
        row = connection.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    if result.get("result_json"):
        result["result"] = json.loads(result["result_json"])
    else:
        result["result"] = None
    result.pop("result_json", None)
    return result


def get_evidence(analysis_id: str) -> list:
    with _LOCK, _connect() as connection:
        rows = connection.execute(
            "SELECT record_json FROM evidence WHERE analysis_id = ? ORDER BY timestamp, rowid",
            (analysis_id,),
        ).fetchall()
    return [json.loads(row["record_json"]) for row in rows]
