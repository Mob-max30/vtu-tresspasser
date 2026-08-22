from database.models import StudentResult, SubjectResult, ResultSource
from validation.validator import validate_student_result

CURRICULUM = {
    "P": {"subjects": [
        {"code": "P1", "name": "Subject A", "credits": 4},
        {"code": "P2", "name": "Subject B", "credits": 3},
    ]},
    "C": {"subjects": [
        {"code": "C1", "name": "Subject X", "credits": 4},
    ]},
}


def make_result(subjects, cycle="P"):
    return StudentResult(
        usn="1RV22CS001", branch="CSE", section="A", cycle=cycle,
        semester=1, subjects=subjects, source=ResultSource.WEBCMD_LIVE,
    )


def test_valid_result_passes():
    result = make_result([
        SubjectResult(code="P1", name="Subject A", credits=4, marks=88, grade="A+"),
        SubjectResult(code="P2", name="Subject B", credits=3, marks=79, grade="A"),
    ])
    v = validate_student_result(result, CURRICULUM)
    assert v.passed
    assert v.errors == []


def test_missing_subject_fails():
    result = make_result([
        SubjectResult(code="P1", name="Subject A", credits=4, marks=88, grade="A+"),
    ])
    v = validate_student_result(result, CURRICULUM)
    assert not v.passed
    assert any("Missing expected subjects" in e for e in v.errors)


def test_unexpected_subject_fails():
    result = make_result([
        SubjectResult(code="P1", name="Subject A", credits=4, marks=88, grade="A+"),
        SubjectResult(code="P2", name="Subject B", credits=3, marks=79, grade="A"),
        SubjectResult(code="P99", name="Ghost Subject", credits=2, marks=50, grade="C"),
    ])
    v = validate_student_result(result, CURRICULUM)
    assert not v.passed
    assert any("Unexpected subjects" in e for e in v.errors)


def test_invalid_grade_fails():
    result = make_result([
        SubjectResult(code="P1", name="Subject A", credits=4, marks=88, grade="Z"),
        SubjectResult(code="P2", name="Subject B", credits=3, marks=79, grade="A"),
    ])
    v = validate_student_result(result, CURRICULUM)
    assert not v.passed
    assert any("Invalid grade" in e for e in v.errors)


def test_duplicate_subject_fails():
    result = make_result([
        SubjectResult(code="P1", name="Subject A", credits=4, marks=88, grade="A+"),
        SubjectResult(code="P1", name="Subject A", credits=4, marks=88, grade="A+"),
    ])
    v = validate_student_result(result, CURRICULUM)
    assert not v.passed
    assert any("Duplicate subject" in e for e in v.errors)


def test_implausible_marks_fails():
    result = make_result([
        SubjectResult(code="P1", name="Subject A", credits=4, marks=150, grade="A+"),
        SubjectResult(code="P2", name="Subject B", credits=3, marks=79, grade="A"),
    ])
    v = validate_student_result(result, CURRICULUM)
    assert not v.passed
    assert any("Implausible marks" in e for e in v.errors)


def test_unknown_cycle_fails():
    result = make_result([
        SubjectResult(code="P1", name="Subject A", credits=4, marks=88, grade="A+"),
    ], cycle="Q")
    v = validate_student_result(result, CURRICULUM)
    assert not v.passed
    assert any("Unknown cycle" in e for e in v.errors)
