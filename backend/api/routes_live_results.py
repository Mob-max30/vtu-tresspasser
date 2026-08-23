from fastapi import APIRouter, HTTPException

from agent.webcmd_live_result import fetch_result

router = APIRouter()


@router.post("/fetch")
def fetch_live_result(usn: str):
    try:
        return fetch_result(usn)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=str(e),
        )