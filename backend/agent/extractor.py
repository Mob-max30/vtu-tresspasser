"""
Normalizes raw webcmd `vtu results` output into the shared StudentResult
schema (database/models.py) — the same shape Track A's CSV importer
produces, so validation/analytics are source-agnostic.

Deterministic DOM/JSON extraction is preferred; an LLM is only worth
reaching for if the adapter's output is genuinely ambiguous (e.g. a
grade column vs a marks-only column depending on scheme) — per README
6.7 / rule 10. This module assumes the adapter already did the
deterministic extraction; it just reshapes the result.
"""

from database.models import StudentResult, SubjectResult, ResultSource, ResultStatus


class ExtractionError(ValueError):
    pass


def extract_student_result(webcmd_output: dict, branch: str, section: str | None, cycle: str) -> StudentResult:
    try:
        usn = webcmd_output["usn"]
        semester = webcmd_output["semester"]
        raw_subjects = webcmd_output["subjects"]
    except KeyError as e:
        raise ExtractionError(f"webcmd output missing required field: {e}")

    subjects = []
    for r in raw_subjects:
        try:
            subjects.append(SubjectResult(
                code=r["code"],
                name=r.get("name", r["code"]),
                credits=float(r["credits"]),
                marks=float(r["marks"]) if r.get("marks") is not None else None,
                grade=r["grade"].strip().upper(),
            ))
        except (KeyError, ValueError) as e:
            raise ExtractionError(f"Malformed subject row {r}: {e}")

    if not subjects:
        raise ExtractionError(f"No subjects extracted for USN {usn} — refusing to fabricate a result")

    return StudentResult(
        usn=usn,
        branch=branch,
        section=section,
        cycle=cycle,
        semester=semester,
        subjects=subjects,
        source=ResultSource.WEBCMD_LIVE,
        status=ResultStatus.PENDING,
    )
