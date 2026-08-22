"""
Deterministic analytics engine.

SGPA  = Σ(credits_i × gradePoint_i) / Σ(credits_i)
CGPA  = Σ(credits_cycle × SGPA_cycle) / Σ(credits_cycle)   [credit-weighted
        across cycles, NOT a plain average — see the earlier webcmd-vtu-agent
        project's lib/grading.js, this is the same formula, ported]

Everything here is pure arithmetic over already-validated data.
Per README rule 9: do not use an LLM for SGPA/statistics calculation.
"""

import statistics
from collections import defaultdict

from database.models import SubjectResult

GRADE_POINTS = {
    "O": 10, "A+": 9, "A": 8, "B+": 7, "B": 6, "C": 5, "P": 4,
    "F": 0, "AB": 0, "W": 0,
}


def compute_sgpa(subjects: list[SubjectResult]) -> dict:
    if not subjects:
        raise ValueError("compute_sgpa: no subjects provided")

    total_credits = 0.0
    earned_points = 0.0
    grade_points_by_code = {}

    for s in subjects:
        grade = s.grade.upper().strip()
        if grade not in GRADE_POINTS:
            raise ValueError(f"compute_sgpa: unknown grade '{s.grade}' for {s.code}")
        gp = GRADE_POINTS[grade]
        total_credits += s.credits
        earned_points += s.credits * gp
        grade_points_by_code[s.code] = gp

    if total_credits == 0:
        raise ValueError("compute_sgpa: total credits is zero")

    return {
        "sgpa": round(earned_points / total_credits, 2),
        "total_credits": total_credits,
        "grade_points_by_code": grade_points_by_code,
    }


def compute_cgpa(cycle_results: list[dict]) -> dict:
    """cycle_results: [{"sgpa": 8.4, "total_credits": 20}, ...]"""
    if not cycle_results:
        raise ValueError("compute_cgpa: no cycles provided")

    total_credits = sum(c["total_credits"] for c in cycle_results)
    if total_credits == 0:
        raise ValueError("compute_cgpa: total credits is zero")

    weighted_sum = sum(c["sgpa"] * c["total_credits"] for c in cycle_results)
    return {"cgpa": round(weighted_sum / total_credits, 2), "total_credits": total_credits}


# ---------------------------------------------------------------------------
# Aggregate rollups (README section 7)
# ---------------------------------------------------------------------------

def section_analytics(students: list[dict]) -> dict:
    """students: [{"sgpa": float, "passed": bool, "grades": [str, ...]}, ...]"""
    sgpas = [s["sgpa"] for s in students if s.get("sgpa") is not None]
    grade_counts = defaultdict(int)
    for s in students:
        for g in s.get("grades", []):
            grade_counts[g] += 1

    return {
        "count": len(students),
        "average_sgpa": round(statistics.mean(sgpas), 2) if sgpas else None,
        "median_sgpa": round(statistics.median(sgpas), 2) if sgpas else None,
        "pass_rate": round(sum(1 for s in students if s.get("passed")) / len(students) * 100, 1) if students else None,
        "grade_distribution": dict(grade_counts),
    }


def branch_analytics(students_by_branch: dict[str, list[dict]]) -> dict:
    return {branch: section_analytics(students) for branch, students in students_by_branch.items()}


def cycle_analytics(students_by_cycle: dict[str, list[dict]]) -> dict:
    return {cycle: section_analytics(students) for cycle, students in students_by_cycle.items()}


def subject_analytics(subject_marks: dict[str, list[float]]) -> dict:
    """subject_marks: { "Mathematics": [87, 74, 91, ...], ... }"""
    result = {}
    for subject, marks in subject_marks.items():
        if not marks:
            continue
        result[subject] = {
            "average": round(statistics.mean(marks), 1),
            "highest": max(marks),
            "lowest": min(marks),
            "pass_percentage": round(sum(1 for m in marks if m >= 40) / len(marks) * 100, 1),
        }
    return result
