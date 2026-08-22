"""
Tracks workflow learning state for the dashboard's "Webcmd workflow:
LEARNED / LEARNING / UNLEARNED" status display. The real source of
truth is webcmd's own site memory (see webcmd_adapter.has_learned_workflow);
this module just keeps a lightweight, UI-friendly log of state
transitions and timestamps for the "Agent Status" panel.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class WorkflowStatus(str, Enum):
    NOT_STARTED = "not_started"
    LEARNING = "learning"
    LEARNED = "learned"
    FAILED = "failed"


@dataclass
class WorkflowStatusLog:
    website: str
    workflow_name: str
    status: WorkflowStatus = WorkflowStatus.NOT_STARTED
    history: list[dict] = field(default_factory=list)

    def transition(self, new_status: WorkflowStatus, note: str = ""):
        self.status = new_status
        self.history.append({
            "status": new_status.value,
            "note": note,
            "at": datetime.now(timezone.utc).isoformat(),
        })

    def to_dict(self) -> dict:
        return {
            "website": self.website,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "history": self.history,
        }


# Single in-memory instance for the hackathon demo — swap for persisted
# state if the workflow needs to survive a backend restart.
vtu_workflow_status = WorkflowStatusLog(website="vtu", workflow_name="vtu/results")
