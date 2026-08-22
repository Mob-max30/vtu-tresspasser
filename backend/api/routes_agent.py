from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.orchestrator import process_live_demo_batch
from agent.webcmd_adapter import ConsentedUSN, ConsentError, MAX_DEMO_BATCH_SIZE
from agent.workflow_manager import vtu_workflow_status
from classification.usn_classifier import ClassifierConfig
from api.routes_project import load_curriculum

router = APIRouter()


class ConsentedUSNIn(BaseModel):
    usn: str
    consent: bool
    consented_by: str


class LiveDemoRequest(BaseModel):
    usns: list[ConsentedUSNIn]
    vtu_session_url: str
    branch_map: dict[str, str]
    section_map: dict[str, str] = {}
    cycle_map: dict[str, str]


@router.post("/run-live-demo")
def run_live_demo(req: LiveDemoRequest):
    """
    TRACK B: small, explicitly consented USN batch (max {cap} — see
    agent/webcmd_adapter.MAX_DEMO_BATCH_SIZE). Demonstrates webcmd's
    explore -> learn -> reuse loop live.
    """.format(cap=MAX_DEMO_BATCH_SIZE)

    consented = [ConsentedUSN(usn=u.usn, consent=u.consent, consented_by=u.consented_by) for u in req.usns]
    config = ClassifierConfig(
        branch_map=req.branch_map,
        section_map=req.section_map,
        cycle_map=req.cycle_map,
    )

    try:
        report = process_live_demo_batch(consented, config, load_curriculum(), req.vtu_session_url)
    except ConsentError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "processed": report.processed,
        "succeeded": report.succeeded,
        "needs_review": report.needs_review,
        "failed": report.failed,  # may include {"status": "captcha_pending", ...} entries
    }


@router.get("/workflow-status")
def workflow_status():
    return vtu_workflow_status.to_dict()
