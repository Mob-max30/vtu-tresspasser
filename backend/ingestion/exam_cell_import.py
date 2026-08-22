"""
TRACK A — Bulk ingestion from an official exam-cell / ERP export.

This is the legitimate path to full-scale (~360 student) analytics:
colleges already receive official VTU result data through their exam
cell. This module reads that already-authorized export and normalizes
it into the same StudentResult shape the live webcmd demo (Track B)
produces, so validation/analytics/dashboard code doesn't need to know
or care which track a given result came from.

Expected CSV columns (adjust to match your actual exam-cell export):
usn, branch, section, cycle, semester, subject_code, subject_name,
credits, marks, grade

One row per (student, subject) — i.e. a student with 6 subjects
occupies 6 rows sharing the same usn/branch/section/cycle/semester.
"""

import csv
from pathlib import Path

from database.models import StudentResult, SubjectResult, ResultSource, ResultStatus
from classification.usn_classifier import validate_usn_format, InvalidUSNError


class ImportError_(ValueError):
    pass


def import_exam_cell_csv(csv_path: Path) -> tuple[list[StudentResult], list[dict]]:
    """Returns (results, row_errors). Never raises for a single bad row —
    a batch of ~360 students shouldn't die because of one malformed line."""

    rows_by_student: dict[str, list[dict]] = {}
    row_errors: list[dict] = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # start=2: header is row 1
            try:
                usn = validate_usn_format(row["usn"])
            except (InvalidUSNError, KeyError) as e:
                row_errors.append({"row": i, "error": str(e)})
                continue
            rows_by_student.setdefault(usn, []).append(row)

    results: list[StudentResult] = []

    for usn, rows in rows_by_student.items():
        try:
            first = rows[0]
            subjects = [
                SubjectResult(
                    code=r["subject_code"],
                    name=r["subject_name"],
                    credits=float(r["credits"]),
                    marks=float(r["marks"]) if r.get("marks") not in (None, "", "NA") else None,
                    grade=r["grade"].strip().upper(),
                )
                for r in rows
            ]
            results.append(StudentResult(
                usn=usn,
                branch=first["branch"],
                section=first.get("section") or None,
                cycle=first["cycle"],
                semester=int(first["semester"]),
                subjects=subjects,
                source=ResultSource.EXAM_CELL_CSV,
                status=ResultStatus.PENDING,
            ))
        except (KeyError, ValueError) as e:
            row_errors.append({"usn": usn, "error": f"Malformed row data: {e}"})

    return results, row_errors
