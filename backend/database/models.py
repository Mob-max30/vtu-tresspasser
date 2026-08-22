"""
Shared data models. Both ingestion paths (exam-cell CSV import, and the
live webcmd demo) must produce this exact shape before handing off to
validation/analytics — that's what keeps the two paths interchangeable.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ResultSource(str, Enum):
    EXAM_CELL_CSV = "exam_cell_csv"   # Track A: official bulk import
    WEBCMD_LIVE = "webcmd_live"       # Track B: consented live demo


class ResultStatus(str, Enum):
    PENDING = "pending"
    VALID = "valid"
    NEEDS_REVIEW = "needs_review"


@dataclass
class SubjectResult:
    code: str
    name: str
    credits: float
    marks: float | None  # may be None if only grade is available
    grade: str


@dataclass
class StudentResult:
    usn: str
    branch: str
    section: str | None
    cycle: str  # "P" or "C"
    semester: int
    subjects: list[SubjectResult]
    source: ResultSource
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: ResultStatus = ResultStatus.PENDING
    validation_errors: list[str] = field(default_factory=list)


# --- SQLite DDL (kept as plain SQL per README 6.9 — SQLite is enough here) ---

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    usn TEXT PRIMARY KEY,
    branch TEXT NOT NULL,
    section TEXT,
    cycle TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usn TEXT NOT NULL REFERENCES students(usn),
    semester INTEGER NOT NULL,
    sgpa REAL,
    total_credits REAL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    retrieved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subject_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER NOT NULL REFERENCES results(id),
    subject_code TEXT NOT NULL,
    subject_name TEXT NOT NULL,
    credits REAL NOT NULL,
    marks REAL,
    grade TEXT NOT NULL,
    grade_points INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    website TEXT NOT NULL,
    workflow_name TEXT NOT NULL,
    workflow_data TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usn TEXT,
    workflow_id INTEGER REFERENCES workflows(id),
    status TEXT NOT NULL,
    error TEXT,
    duration_ms INTEGER,
    timestamp TEXT NOT NULL
);
"""
