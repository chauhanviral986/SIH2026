# database/database.py

import json
import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent
    / "screening.db"
)


def init_db():
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DB_PATH
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS screenings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            file_name TEXT,
            file_hash TEXT,
            document_type TEXT,
            name TEXT,
            document_number TEXT,
            risk_score REAL,
            risk_level TEXT,
            result_json TEXT
        )
        """
    )

    connection.commit()
    connection.close()


def save_screening(record):
    init_db()

    connection = sqlite3.connect(
        DB_PATH
    )

    cursor = connection.cursor()

    timestamp = datetime.now().isoformat(
        timespec="seconds"
    )

    cursor.execute(
        """
        INSERT INTO screenings (
            timestamp,
            file_name,
            file_hash,
            document_type,
            name,
            document_number,
            risk_score,
            risk_level,
            result_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp,
            record.get("file_name", ""),
            record.get("file_hash", ""),
            record.get(
                "document_type",
                "",
            ),
            record.get(
                "name",
                "",
            ),
            record.get(
                "document_number",
                "",
            ),
            record.get(
                "risk_score",
                0,
            ),
            record.get(
                "risk_level",
                "",
            ),
            json.dumps(
                record,
                default=str,
            ),
        ),
    )

    connection.commit()
    connection.close()