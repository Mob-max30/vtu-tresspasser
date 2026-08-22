"""
TRACK B — Live webcmd demo adapter.

This is the "explore -> learn -> reuse" demonstration piece, run against
a SMALL, EXPLICITLY CONSENTING list of USNs (teammates checking their
own results). It is NOT the path to the 360-student dataset — that's
Track A (ingestion/exam_cell_import.py).

Webcmd CLI surface used here (verified against installed webcmd 0.7.4):

  webcmd session create -f json
  webcmd --session <id> browser run --stdin
  webcmd --session <id> browser snapshot
  webcmd browser verify vtu/results
  webcmd site memory show vtu
  webcmd session close <id>

CAPTCHA handling follows webcmd's documented convention. This module
does NOT attempt to solve or bypass CAPTCHA.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Hard guardrail
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
        super().__init__(
            f"CAPTCHA verification required. Run: {verify_command}"
        )


class WorkflowState(str, Enum):
    UNLEARNED = "unlearned"
    LEARNED = "learned"


@dataclass
class ConsentedUSN:
    usn: str
    consent: bool
    consented_by: str


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

        non_consenting = [
            u.usn for u in self.usns if not u.consent
        ]

        if non_consenting:
            raise ConsentError(
                f"USNs missing explicit consent: {non_consenting}"
            )


def _run_webcmd(
    args: list[str],
    stdin_data: str | None = None,
) -> dict:
    """
    Run the installed Webcmd CLI.

    Windows note:
    `webcmd` is installed globally by npm as `webcmd.cmd`.
    `shutil.which()` resolves the actual executable path so Python's
    subprocess can invoke it reliably.
    """

    webcmd = shutil.which("webcmd")

    if not webcmd:
        raise WebcmdAgentError(
            "webcmd CLI not found on PATH. "
            "Run `where.exe webcmd` to verify the installation."
        )

    proc = subprocess.run(
        [webcmd, *args],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=120,
        shell=False,
    )

    if proc.returncode != 0:
        raise WebcmdAgentError(
            f"webcmd {' '.join(args)} failed: "
            f"{proc.stderr.strip()}"
        )

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"raw": proc.stdout}


class WebcmdVTUAdapter:
    """Exposes the conceptual operations from the README."""

    def __init__(self):
        self.session_id: str | None = None
        self.workflow_state = WorkflowState.UNLEARNED

    def start_browser(self):
        result = _run_webcmd(
            ["session", "create", "-f", "json"]
        )

        # Webcmd 0.7.4 returns the session identifier in `id`.
        self.session_id = result.get("id")

        if not self.session_id:
            raise WebcmdAgentError(
                f"Could not parse session id from: {result}"
            )

        return self.session_id

    def has_learned_workflow(self) -> bool:
        """
        Check Webcmd's site memory for a prior VTU workflow.
        """

        try:
            _run_webcmd(
                ["site", "memory", "show", "vtu"]
            )

            self.workflow_state = WorkflowState.LEARNED
            return True

        except WebcmdAgentError:
            return False

    def explore_workflow(self, session_url: str):
        """
        First-run reconnaissance.

        Uses Webcmd browser run to navigate to the supplied page and
        inspect it. This is reconnaissance only; it does not attempt
        to solve CAPTCHA.
        """

        if not self.session_id:
            raise WebcmdAgentError(
                "start_browser() must run before explore_workflow()"
            )

        recon_script = f"""
        await page.goto('{session_url}');
        return await page.accessibility.snapshot();
        """

        snapshot = _run_webcmd(
            [
                "--session",
                self.session_id,
                "browser",
                "run",
                "--stdin",
            ],
            stdin_data=recon_script,
        )

        return snapshot

    def execute_workflow(self, usn: str) -> dict:
        """
        Execute an already-authored VTU Webcmd adapter.
        """

        if self.workflow_state != WorkflowState.LEARNED:
            raise WebcmdAgentError(
                "No learned workflow — call explore_workflow "
                "+ author the adapter first"
            )

        if not self.session_id:
            raise WebcmdAgentError(
                "Browser session has not been started."
            )

        result = _run_webcmd(
            [
                "--session",
                self.session_id,
                "vtu",
                "results",
                "--usn",
                usn,
                "-f",
                "json",
            ]
        )

        if result.get("action_required"):
            raise CaptchaPending(
                verify_command=result["verify_command"],
                session_id=self.session_id,
            )

        return result

    def resume_after_captcha(
        self,
        verify_command: str,
    ) -> dict:
        """
        Resume after a human reports that CAPTCHA has been completed.
        """

        return _run_webcmd(
            verify_command.split()
        )

    def save_workflow(self):
        """
        Webcmd site memory persists the workflow once the adapter
        has been verified.
        """

        self.workflow_state = WorkflowState.LEARNED

    def load_workflow(self) -> bool:
        return self.has_learned_workflow()

    def stop_browser(self):
        """
        Close the active Webcmd session.
        """

        if self.session_id:
            try:
                _run_webcmd(
                    [
                        "session",
                        "close",
                        self.session_id,
                    ]
                )
            finally:
                self.session_id = None