"""
Validates a StudentResult against the expected curriculum structure
before it's trusted enough to save/count in analytics.

Deterministic — no LLM (README rule 9).
"""

from dataclasses import dataclass

from database.models import StudentResult
from analytics.analytics import GRADE_POINTS

VALID_GRADES = set(GRADE_POINTS.keys())


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str]


def validate_student_result(result: StudentResult, curriculum: dict) -> ValidationResult:
    errors: list[str] = []

    cycle_config = curriculum.get(result.cycle)
    if cycle_config is None:
        errors.append(f"Unknown cycle '{result.cycle}' — not present in curriculum config")
        return ValidationResult(passed=False, errors=errors)

    expected_codes = {s["code"] for s in cycle_config["subjects"]}
    extracted_codes = {s.code for s in result.subjects}

    missing = expected_codes - extracted_codes
    unexpected = extracted_codes - expected_codes
    if missing:
        errors.append(f"Missing expected subjects: {sorted(missing)}")
    if unexpected:
        errors.append(f"Unexpected subjects present: {sorted(unexpected)}")

    seen_codes = set()
    for s in result.subjects:
        if s.code in seen_codes:
            errors.append(f"Duplicate subject entry: {s.code}")
        seen_codes.add(s.code)

        if s.grade.upper() not in VALID_GRADES:
            errors.append(f"Invalid grade '{s.grade}' for subject {s.code}")

        if s.credits < 0 or s.credits > 10:
            errors.append(f"Implausible credits ({s.credits}) for subject {s.code}")

        if s.marks is not None and not (0 <= s.marks <= 100):
            errors.append(f"Implausible marks ({s.marks}) for subject {s.code}")

    if len(result.subjects) != len(cycle_config["subjects"]):
        errors.append(
            f"Subject count mismatch: expected {len(cycle_config['subjects'])}, "
            f"got {len(result.subjects)}"
        )

    return ValidationResult(passed=(len(errors) == 0), errors=errors)
