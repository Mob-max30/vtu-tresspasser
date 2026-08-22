"""
TRACK B — Live webcmd demo adapter.

This is the "explore -> learn -> reuse" demonstration piece, run against
a SMALL, EXPLICITLY CONSENTING list of USNs (teammates checking their
own results). It is NOT the path to the 360-student dataset — that's
Track A (ingestion/exam_cell_import.py).

Two guardrails are enforced HERE, in code, not just in the README:
  1. MAX_DEMO_BATCH_SIZE caps how many USNs a single run can touch.
  2. Every USN must appear in `consented_usns` with consent=True.
Both exist so "just raise the limit for the real run" isn't a one-line
change — see MAX_DEMO_BATCH_SIZE's docstring below before touching it.

Webcmd CLI surface used here (verified against installed webcmd 0.7.4,
see /adapter/webcmd-cli-reference.md in this repo — do not invent
commands beyond what's documented there):

  webcmd session create -f json
  webcmd --session <id> browser run --stdin      (Playwright JS, recon only)
  webcmd --session <id> browser snapshot          (accessibility snapshot)
  webcmd browser verify vtu/results                (once the adapter file
                                                     at ~/.webcmd/clis/vtu/results.js
                                                     is authored — see Phase 2)
  webcmd site memory show vtu                      (inspect learned knowledge)
  webcmd session close <id>

CAPTCHA handling follows webcmd's own documented convention: the
adapter returns {"action_required": true, "verify_command": ...} when
it hits a captcha; this module surfaces that to the caller (FastAPI ->
frontend) and does NOT attempt to solve or bypass it. Execution only
resumes after the human reports completion and verification succeeds.
"""

import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum

# ---------------------------------------------------------------------------
# Hard guardrail. Do not remove or silently raise this for "just one big run."
# If you genuinely need more students processed live, that's Track A's job
# (an authorized bulk export) — not scaling up interactive browser sessions
# against a public single-lookup portal.
# ---------------------------------------------------------------------------
MAX_DEMO_BATCH_SIZE = 10


class WebcmdAgentError(Exception):
    pass


class ConsentError(WebcmdAgentError):
    pass


class CaptchaPending(WebcmdAgentError):
    """Raised to signal the orchestrator must pause for human input."""
    def __init__(self, verify_command: str, session_id: str):
        self.verify_command = verify_command
        self.session_id = session_id
        super().__init__(f"CAPTCHA verification required. Run: {verify_command}")


class WorkflowState(str, Enum):
    UNLEARNED = "unlearned"
    LEARNED = "learned"


@dataclass
class ConsentedUSN:
    usn: str
    consent: bool
    consented_by: str  # who confirmed consent (e.g. the student's own name)


@dataclass
class DemoBatch:
    usns: list[ConsentedUSN]

    def __post_init__(self):
        if len(self.usns) > MAX_DEMO_BATCH_SIZE:
            raise ConsentError(
                f"Track B demo batch of {len(self.usns)} exceeds the "
                f"{MAX_DEMO_BATCH_SIZE}-USN cap. Bulk processing belongs "
                f"in Track A (authorized exam-cell import), not here."
            )
        non_consenting = [u.usn for u in self.usns if not u.consent]
        if non_consenting:
            raise ConsentError(f"USNs missing explicit consent: {non_consenting}")


def _run_webcmd(args: list[str], stdin_data: str | None = None) -> dict:
    """Thin subprocess wrapper. Raises WebcmdAgentError on non-zero exit."""
    proc = subprocess.run(
        ["webcmd", *args],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise WebcmdAgentError(f"webcmd {' '.join(args)} failed: {proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"raw": proc.stdout}


class WebcmdVTUAdapter:
    """Exposes the conceptual operations from the README (6.6 / Prompt 2)."""

    def __init__(self):
        self.session_id: str | None = None
        self.workflow_state = WorkflowState.UNLEARNED

    def start_browser(self):
        result = _run_webcmd(["session", "create", "-f", "json"])
        self.session_id = result.get("sessionId") or result.get("session_id")
        if not self.session_id:
            raise WebcmdAgentError(f"Could not parse session id from: {result}")
        return self.session_id

    def has_learned_workflow(self) -> bool:
        """Checks webcmd's own site memory for a prior vtu adapter, rather
        than tracking this ourselves — memory is the actual source of truth."""
        try:
            _run_webcmd(["site", "memory", "show", "vtu"])
            self.workflow_state = WorkflowState.LEARNED
            return True
        except WebcmdAgentError:
            return False

    def explore_workflow(self, session_url: str):
        """
        FIRST RUN ONLY. Drives ad-hoc Playwright JS via `browser run` to
        locate the USN field, captcha image, and submit control. This is
        recon — its output becomes the adapter file at
        ~/.webcmd/clis/vtu/results.js, authored by a human/agent afterward
        via `webcmd browser init vtu/results`, NOT auto-generated here.
        """
        if not self.session_id:
            raise WebcmdAgentError("start_browser() must run before explore_workflow()")

        recon_script = f"""
        await page.goto('{session_url}');
        return await page.accessibility.snapshot();
        """
        snapshot = _run_webcmd(
            ["--session", self.session_id, "browser", "run", "--stdin"],
            stdin_data=recon_script,
        )
        return snapshot  # human/agent reviews this to author the adapter

    def execute_workflow(self, usn: str) -> dict:
        """
        SUBSEQUENT RUNS. Uses the already-authored, already-verified
        `vtu/results` adapter command instead of re-exploring the DOM.
        Raises CaptchaPending if VTU presents a captcha — the caller
        (orchestrator) must pause for a human, then call resume_after_captcha.
        """
        if self.workflow_state != WorkflowState.LEARNED:
            raise WebcmdAgentError("No learned workflow — call explore_workflow + author the adapter first")

        result = _run_webcmd(
            ["--session", self.session_id, "vtu", "results", "--usn", usn, "-f", "json"]
        )

        if result.get("action_required"):
            raise CaptchaPending(
                verify_command=result["verify_command"],
                session_id=self.session_id,
            )

        return result

    def resume_after_captcha(self, verify_command: str) -> dict:
        """Called only after a human reports the captcha is solved."""
        return _run_webcmd(verify_command.split())

    def save_workflow(self):
        # webcmd's site memory persists automatically once `browser verify`
        # passes; this is a light wrapper for orchestrator readability.
        self.workflow_state = WorkflowState.LEARNED

    def load_workflow(self) -> bool:
        return self.has_learned_workflow()

    def stop_browser(self):
        if self.session_id:
            _run_webcmd(["session", "close", self.session_id])
            self.session_id = None
