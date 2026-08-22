"""
Simple retry/re-discovery, per README section 9:
"Do not attempt to implement an enormous autonomous recovery system.
A simple retry/re-discovery mechanism is enough for the hackathon."
"""

import logging
from dataclasses import dataclass

from agent.webcmd_adapter import WebcmdVTUAdapter, WebcmdAgentError, CaptchaPending

logger = logging.getLogger("vtu_agent.recovery")


@dataclass
class RecoveryResult:
    succeeded: bool
    attempts: int
    final_error: str | None = None


def execute_with_recovery(adapter: WebcmdVTUAdapter, usn: str, max_retries: int = 1) -> tuple[dict | None, RecoveryResult]:
    """
    Attempt execute_workflow, and on failure (excluding CaptchaPending,
    which must bubble up for human handling — it is not a failure to
    retry around) try once more after re-checking the learned workflow.
    """
    attempts = 0
    last_error = None

    while attempts <= max_retries:
        attempts += 1
        try:
            result = adapter.execute_workflow(usn)
            return result, RecoveryResult(succeeded=True, attempts=attempts)
        except CaptchaPending:
            raise  # not a failure — must be surfaced to the orchestrator/user
        except WebcmdAgentError as e:
            last_error = str(e)
            logger.warning("execute_workflow failed for %s (attempt %d): %s", usn, attempts, last_error)
            if attempts <= max_retries:
                logger.info("Re-checking learned workflow before retry for %s", usn)
                adapter.load_workflow()

    return None, RecoveryResult(succeeded=False, attempts=attempts, final_error=last_error)
