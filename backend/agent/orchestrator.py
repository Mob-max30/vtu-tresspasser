"""
Agent orchestrator — the decision loop from README 6.5 / 16.

Two entry points, matching the two tracks:
  process_bulk_import(...)   Track A — already-authorized CSV data.
                              No browser involved; classify -> validate -> save.
  process_live_demo_batch(...) Track B — small, consented USN list.
                              classify -> (explore-or-reuse) webcmd -> extract
                              -> validate -> save, with recovery + captcha pause.

Both converge on the same validate/save/analytics pipeline, per the
project's normalized StudentResult schema.
"""

import logging
from dataclasses import dataclass

from classification.usn_classifier import classify_batch, ClassifierConfig, InvalidUSNError
from ingestion.exam_cell_import import import_exam_cell_csv
from agent.webcmd_adapter import WebcmdVTUAdapter, DemoBatch, ConsentedUSN, CaptchaPending, ConsentError
from agent.extractor import extract_student_result, ExtractionError
from agent.recovery import execute_with_recovery
from agent.workflow_manager import vtu_workflow_status, WorkflowStatus
from validation.validator import validate_student_result
from database.database import save_student_result
from database.models import StudentResult, ResultStatus

logger = logging.getLogger("vtu_agent.orchestrator")


@dataclass
class ProcessingReport:
    processed: int = 0
    succeeded: int = 0
    needs_review: int = 0
    failed: list[dict] = None

    def __post_init__(self):
        if self.failed is None:
            self.failed = []


# ---------------------------------------------------------------------------
# TRACK A — bulk, authorized CSV import
# ---------------------------------------------------------------------------

def process_bulk_import(csv_path, curriculum: dict) -> ProcessingReport:
    results, row_errors = import_exam_cell_csv(csv_path)
    report = ProcessingReport(failed=list(row_errors))

    for result in results:
        report.processed += 1
        validation = validate_student_result(result, curriculum)
        if validation.passed:
            result.status = ResultStatus.VALID
            save_student_result(result)
            report.succeeded += 1
        else:
            result.status = ResultStatus.NEEDS_REVIEW
            result.validation_errors = validation.errors
            save_student_result(result)
            report.needs_review += 1

    return report


# ---------------------------------------------------------------------------
# TRACK B — small, consented live webcmd demo
# ---------------------------------------------------------------------------

def process_live_demo_batch(
    consented_usns: list[ConsentedUSN],
    classifier_config: ClassifierConfig,
    curriculum: dict,
    vtu_session_url: str,
) -> ProcessingReport:
    """
    Raises ConsentError immediately (before touching a browser) if the
    batch violates the size cap or consent requirement — see
    agent/webcmd_adapter.py's DemoBatch for the enforced guardrail.
    """
    batch = DemoBatch(usns=consented_usns)  # raises ConsentError on violation

    metadata_list, classify_errors = classify_batch([u.usn for u in batch.usns], classifier_config)
    report = ProcessingReport(failed=list(classify_errors))

    adapter = WebcmdVTUAdapter()
    adapter.start_browser()

    if not adapter.has_learned_workflow():
        vtu_workflow_status.transition(WorkflowStatus.LEARNING, note="No prior site memory found")
        adapter.explore_workflow(vtu_session_url)
        # NOTE: authoring the actual ~/.webcmd/clis/vtu/results.js adapter
        # from this recon output, then running `webcmd browser verify
        # vtu/results`, is a human/agent step done once outside this loop
        # (Phase 2/3 of the build) — not auto-generated at runtime here.
        adapter.save_workflow()
        vtu_workflow_status.transition(WorkflowStatus.LEARNED, note="Adapter verified")
    else:
        vtu_workflow_status.transition(WorkflowStatus.LEARNED, note="Reusing existing site memory")

    for meta in metadata_list:
        report.processed += 1
        try:
            raw_result, recovery_info = execute_with_recovery(adapter, meta.usn)
        except CaptchaPending as pending:
            # Surface to caller (FastAPI route) so the frontend can show
            # the "solve CAPTCHA, then Continue" prompt for this USN.
            report.failed.append({
                "usn": meta.usn,
                "status": "captcha_pending",
                "verify_command": pending.verify_command,
            })
            continue

        if raw_result is None:
            report.failed.append({"usn": meta.usn, "error": recovery_info.final_error})
            continue

        try:
            result = extract_student_result(raw_result, meta.branch, meta.section, meta.cycle)
        except ExtractionError as e:
            report.failed.append({"usn": meta.usn, "error": str(e)})
            continue

        validation = validate_student_result(result, curriculum)
        result.status = ResultStatus.VALID if validation.passed else ResultStatus.NEEDS_REVIEW
        result.validation_errors = validation.errors
        save_student_result(result)

        if validation.passed:
            report.succeeded += 1
        else:
            report.needs_review += 1

    adapter.stop_browser()
    return report
