import pytest
from classification.usn_classifier import (
    classify_usn, classify_batch, validate_usn_format,
    ClassifierConfig, InvalidUSNError,
)


@pytest.fixture
def config():
    return ClassifierConfig(
        branch_map={"CS": "CSE", "AI": "AIML", "EC": "ECE"},
        section_map={"1RV22CS001": "A", "1RV22AI010": "B"},
        cycle_map={"CSE": "P", "AIML": "P", "ECE": "C"},
    )


def test_valid_cse_usn(config):
    result = classify_usn("1rv22cs001", config)  # lowercase input, should normalize
    assert result.usn == "1RV22CS001"
    assert result.branch == "CSE"
    assert result.section == "A"
    assert result.cycle == "P"


def test_valid_aiml_usn(config):
    result = classify_usn("1RV22AI010", config)
    assert result.branch == "AIML"
    assert result.section == "B"
    assert result.cycle == "P"


def test_valid_ece_usn(config):
    result = classify_usn("1RV22EC050", config)
    assert result.branch == "ECE"
    assert result.cycle == "C"
    assert result.section is None  # unmapped section is allowed, not an error


def test_invalid_usn_format(config):
    with pytest.raises(InvalidUSNError):
        classify_usn("NOT-A-USN", config)


def test_unknown_branch_code(config):
    with pytest.raises(InvalidUSNError):
        classify_usn("1RV22ME001", config)  # ME not in branch_map


def test_validate_usn_format_normalizes_case():
    assert validate_usn_format("1rv22cs001") == "1RV22CS001"


def test_classify_batch_isolates_bad_rows(config):
    usns = ["1RV22CS001", "GARBAGE", "1RV22AI010", "1RV22XX999"]
    successes, failures = classify_batch(usns, config)
    assert len(successes) == 2
    assert len(failures) == 2
    assert failures[0]["usn"] == "GARBAGE"
