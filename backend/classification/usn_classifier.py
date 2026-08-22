"""
Deterministic USN -> {branch, section, cycle} classifier.

Per the project's non-negotiable rules: NO LLM here. This is pure
string/lookup logic, fully unit-testable, fully deterministic.

VTU USN shape (standard 10-char format): 1RV22CS045
  1        - college code prefix (varies)
  RV       - college identifier
  22       - joining year
  CS       - branch code
  045      - roll number within branch

We don't hardcode which specific roll numbers fall in which *section*
or which *cycle* (P vs C) — those come from the mapping files the user
uploads, since they vary by college and even by year. This module
resolves a USN against those mappings; it does not guess.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

USN_PATTERN = re.compile(r"^\d[A-Z]{2}\d{2}[A-Z]{2}\d{3}$")


class InvalidUSNError(ValueError):
    pass


@dataclass
class USNMetadata:
    usn: str
    branch: str
    section: Optional[str]
    cycle: Optional[str]  # "P" or "C"


@dataclass
class ClassifierConfig:
    """
    branch_map:   { "CS": "CSE", "AI": "AIML", "EC": "ECE", ... }
    section_map:  { "1RV22CS001": "A", ... }  OR a roll-number-range rule;
                  kept as an explicit dict for hackathon simplicity —
                  swap in a range-based resolver later if needed.
    cycle_map:    { "CSE": "P", "AIML": "P", "ECE": "C", ... }
                  branch-level P/C assignment (this is how VTU actually
                  splits first-years into cycles).
    """
    branch_map: dict
    section_map: dict
    cycle_map: dict

    @staticmethod
    def from_csv_files(branch_csv: Path, section_csv: Path, cycle_csv: Path) -> "ClassifierConfig":
        def read_pairs(path):
            with open(path, newline="", encoding="utf-8") as f:
                return {row[0].strip(): row[1].strip() for row in csv.reader(f) if row}

        return ClassifierConfig(
            branch_map=read_pairs(branch_csv),
            section_map=read_pairs(section_csv),
            cycle_map=read_pairs(cycle_csv),
        )


def validate_usn_format(usn: str) -> str:
    usn = usn.strip().upper()
    if not USN_PATTERN.match(usn):
        raise InvalidUSNError(f"'{usn}' does not match expected USN format (e.g. 1RV22CS001)")
    return usn


def extract_branch_code(usn: str) -> str:
    # positions 5-6 (0-indexed) in a validated 10-char USN, e.g. "1RV22CS001" -> "CS"
    return usn[5:7]


def classify_usn(usn: str, config: ClassifierConfig) -> USNMetadata:
    usn = validate_usn_format(usn)
    branch_code = extract_branch_code(usn)

    branch = config.branch_map.get(branch_code)
    if branch is None:
        raise InvalidUSNError(f"Unknown branch code '{branch_code}' for USN {usn}")

    section = config.section_map.get(usn)  # may legitimately be None if unmapped
    cycle = config.cycle_map.get(branch)    # P or C, keyed by resolved branch name

    return USNMetadata(usn=usn, branch=branch, section=section, cycle=cycle)


def classify_batch(usns: list[str], config: ClassifierConfig) -> tuple[list[USNMetadata], list[dict]]:
    """Returns (successes, failures). Never raises for a single bad row —
    bad rows are collected so a batch of 360 doesn't die on row 217."""
    successes: list[USNMetadata] = []
    failures: list[dict] = []
    for raw in usns:
        try:
            successes.append(classify_usn(raw, config))
        except InvalidUSNError as e:
            failures.append({"usn": raw, "error": str(e)})
    return successes, failures
