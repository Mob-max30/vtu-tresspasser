from fastapi import APIRouter

from database.database import get_connection
from analytics.analytics import section_analytics, branch_analytics, cycle_analytics

router = APIRouter()


def _rows_to_student_dicts(rows) -> list[dict]:
    return [
        {"sgpa": r["sgpa"], "passed": r["status"] == "valid", "grades": []}
        for r in rows
    ]


@router.get("/overview")
def overview():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM results").fetchall()
    return section_analytics(_rows_to_student_dicts(rows))


@router.get("/branch")
def branch():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT s.branch, r.sgpa, r.status FROM students s JOIN results r ON s.usn = r.usn"
        ).fetchall()

    by_branch: dict[str, list] = {}
    for r in rows:
        by_branch.setdefault(r["branch"], []).append(r)

    return branch_analytics({b: _rows_to_student_dicts(rs) for b, rs in by_branch.items()})


@router.get("/cycle")
def cycle():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT s.cycle, r.sgpa, r.status FROM students s JOIN results r ON s.usn = r.usn"
        ).fetchall()

    by_cycle: dict[str, list] = {}
    for r in rows:
        by_cycle.setdefault(r["cycle"], []).append(r)

    return cycle_analytics({c: _rows_to_student_dicts(rs) for c, rs in by_cycle.items()})


@router.get("/subject")
def subject():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT subject_name, marks FROM subject_results WHERE marks IS NOT NULL"
        ).fetchall()

    marks_by_subject: dict[str, list] = {}
    for r in rows:
        marks_by_subject.setdefault(r["subject_name"], []).append(r["marks"])

    from analytics.analytics import subject_analytics
    return subject_analytics(marks_by_subject)
