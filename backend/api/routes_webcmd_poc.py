from fastapi import APIRouter, HTTPException

from agent.webcmd_poc import run_browser_proof_of_concept, WebcmdPoCError, DEFAULT_TEST_URL

router = APIRouter()


@router.post("/test")
def webcmd_poc_test(url: str = DEFAULT_TEST_URL):
    """
    Smallest possible proof that this backend can genuinely invoke Webcmd
    0.7.4 and control a browser end-to-end:

        FastAPI -> webcmd session create -> browser run (navigate)
        -> browser snapshot -> session close -> return

    Does NOT touch VTU. Does NOT process any USNs. This is purely an
    infrastructure/wiring check before the real adapter work begins.
    """
    try:
        result = run_browser_proof_of_concept(url)
    except WebcmdPoCError as e:
        raise HTTPException(
            status_code=502,
            detail={"message": str(e), "webcmd_error_code": e.code},
        )
    return result
