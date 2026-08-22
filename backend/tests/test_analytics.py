import pytest
from database.models import SubjectResult
from analytics.analytics import compute_sgpa, compute_cgpa, section_analytics, subject_analytics


def test_compute_sgpa_matches_known_value():
    subjects = [
        SubjectResult(code="P1", name="A", credits=4, marks=88, grade="A"),
        SubjectResult(code="P2", name="B", credits=4, marks=95, grade="O"),
        SubjectResult(code="P3", name="C", credits=3, marks=70, grade="B+"),
        SubjectResult(code="P4", name="D", credits=1, marks=90, grade="A+"),
        SubjectResult(code="P5", name="E", credits=1, marks=95, grade="O"),
        SubjectResult(code="P6", name="F", credits=1.5, marks=88, grade="A"),
    ]
    result = compute_sgpa(subjects)
    # matches the same sample data used in the earlier webcmd-vtu-agent/cli.js check
    assert result["sgpa"] == 8.55
    assert result["total_credits"] == 14.5


def test_compute_cgpa_is_credit_weighted_not_plain_average():
    cycles = [
        {"sgpa": 8.55, "total_credits": 14.5},
        {"sgpa": 8.38, "total_credits": 13},
    ]
    result = compute_cgpa(cycles)
    assert result["cgpa"] == 8.47
    # plain average would be 8.465 (rounds to 8.47 too here, so also check
    # a case where weighting clearly matters):
    skewed = compute_cgpa([{"sgpa": 10, "total_credits": 1}, {"sgpa": 5, "total_credits": 20}])
    assert skewed["cgpa"] != round((10 + 5) / 2, 2)


def test_compute_sgpa_rejects_unknown_grade():
    with pytest.raises(ValueError):
        compute_sgpa([SubjectResult(code="P1", name="A", credits=4, marks=88, grade="Q")])


def test_section_analytics_basic():
    students = [
        {"sgpa": 8.0, "passed": True, "grades": ["A", "B"]},
        {"sgpa": 9.0, "passed": True, "grades": ["O", "A"]},
        {"sgpa": 4.0, "passed": False, "grades": ["F", "P"]},
    ]
    stats = section_analytics(students)
    assert stats["count"] == 3
    assert stats["average_sgpa"] == 7.0
    assert stats["pass_rate"] == pytest.approx(66.7, abs=0.1)


def test_subject_analytics_basic():
    marks = {"Mathematics": [80, 60, 30, 90]}
    stats = subject_analytics(marks)
    assert stats["Mathematics"]["average"] == 65.0
    assert stats["Mathematics"]["highest"] == 90
    assert stats["Mathematics"]["lowest"] == 30
    assert stats["Mathematics"]["pass_percentage"] == 75.0
