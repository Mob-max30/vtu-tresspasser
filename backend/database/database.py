import sqlite3
from contextlib import contextmanager
from pathlib import Path

from database.models import StudentResult, SCHEMA_SQL

DB_PATH = Path(__file__).parent / "vtu_results.db"


def init_db(db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


@contextmanager
def get_connection(db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_student_result(result: StudentResult, db_path: Path = DB_PATH):
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO students (usn, branch, section, cycle) VALUES (?, ?, ?, ?)",
            (result.usn, result.branch, result.section, result.cycle),
        )

        from analytics.analytics import compute_sgpa  # local import avoids circular import
        sgpa_info = compute_sgpa(result.subjects)

        cur = conn.execute(
            """INSERT INTO results (usn, semester, sgpa, total_credits, status, source, retrieved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (result.usn, result.semester, sgpa_info["sgpa"], sgpa_info["total_credits"],
             result.status.value, result.source.value, result.retrieved_at),
        )
        result_id = cur.lastrowid

        for s in result.subjects:
            conn.execute(
                """INSERT INTO subject_results
                   (result_id, subject_code, subject_name, credits, marks, grade, grade_points)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (result_id, s.code, s.name, s.credits, s.marks, s.grade,
                 sgpa_info["grade_points_by_code"].get(s.code, 0)),
            )
        return result_id
