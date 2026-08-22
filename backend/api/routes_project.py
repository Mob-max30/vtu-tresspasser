import json
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, HTTPException

from agent.orchestrator import process_bulk_import

router = APIRouter()

CURRICULUM_PATH = Path(__file__).parent.parent / "curriculum" / "config.json"


def load_curriculum() -> dict:
    with open(CURRICULUM_PATH) as f:
        return json.load(f)


@router.post("/upload-exam-cell-csv")
async def upload_exam_cell_csv(file: UploadFile):
    """
    TRACK A: accepts an official exam-cell / ERP export CSV and runs the
    full classify -> validate -> save pipeline against it. This is the
    legitimate path to full-scale (e.g. ~360 student) analytics.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Expected a .csv file")

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        curriculum = load_curriculum()
        report = process_bulk_import(tmp_path, curriculum)
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "processed": report.processed,
        "succeeded": report.succeeded,
        "needs_review": report.needs_review,
        "failed": report.failed,
    }


@router.get("/curriculum")
def get_curriculum():
    return load_curriculum()
