from fastapi import APIRouter, HTTPException

from database.database import get_connection

router = APIRouter()


@router.get("")
def list_results():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT s.usn, s.branch, s.section, s.cycle, r.semester, r.sgpa, r.status, r.source "
            "FROM students s JOIN results r ON s.usn = r.usn"
        ).fetchall()
        return [dict(row) for row in rows]


@router.get("/{usn}")
def get_result(usn: str):
    with get_connection() as conn:
        student = conn.execute("SELECT * FROM students WHERE usn = ?", (usn,)).fetchone()
        if not student:
            raise HTTPException(status_code=404, detail=f"No result for USN {usn}")

        result_row = conn.execute(
            "SELECT * FROM results WHERE usn = ? ORDER BY id DESC LIMIT 1", (usn,)
        ).fetchone()
        subjects = conn.execute(
            "SELECT * FROM subject_results WHERE result_id = ?", (result_row["id"],)
        ).fetchall()

        return {
            "student": dict(student),
            "result": dict(result_row),
            "subjects": [dict(s) for s in subjects],
        }
