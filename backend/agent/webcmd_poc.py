"""
SMALLEST POSSIBLE PROOF OF CONCEPT that this backend can genuinely invoke
Webcmd 0.7.4 and control a browser.

Pipeline (per Master README constraints):
    FastAPI endpoint -> webcmd 0.7.4 -> browser session
    -> open a harmless test webpage -> browser snapshot -> return

Uses ONLY commands verified against the actual installed webcmd 0.7.4
CLI in this session (via `webcmd <cmd> --help` and live execution):

    webcmd session create -f json
    webcmd --session <id> browser run --stdin      (Playwright navigation)
    webcmd --session <id> browser snapshot          (NOTE: does not accept -f/--format)
    webcmd session close <id>

Confirmed real output shapes (captured from a live successful run):
    session create -> {"id": "session_...", "kind": "explicit"}
        NOTE: the field is "id", not "sessionId" or "session_id".
    browser run     -> {"ok": true, "result": ..., "page": {...}, "snapshotDiff": ..., "timings": {...}}
    browser snapshot -> {"ok": true, "tree": "<page ...>...</page>", "page": {...}, "warnings": [], "limits": {...}}
    session close   -> plain text: "closed: true\\nalreadyIdle: false\\nsession: session_..."
        NOTE: close does NOT return JSON even with -f json in some cases in
        this version's CLI output for this subcommand - parsed defensively below.

Confirmed real error shape (captured from a live failed run):
    {"error": {"code": "runtime_command_failed", "message": "..."}}
    {"error": {"code": "session_not_found", "message": "...", "hint": "..."}}

Does NOT touch VTU. Does NOT process any USNs. Pure infrastructure check,
per the Master README's explicit scope for this step.

OPERATIONAL NOTE: webcmd 0.7.4's CloakBrowser runtime is hardcoded
`headless: false` — it always launches a real, visible browser window.
On a normal desktop (e.g. your Mac) this just works. On a headless
server/CI box with no display, you need a virtual display (e.g. Xvfb on
Linux) running before the webcmd daemon starts, or this will fail with
"Missing X server or $DISPLAY".
"""

import json
import subprocess

DEFAULT_TEST_URL = "https://example.com"


class WebcmdPoCError(Exception):
    """Raised whenever a webcmd invocation fails or returns an error shape."""
    def __init__(self, message: str, code: str | None = None, raw: dict | None = None):
        self.code = code
        self.raw = raw
        super().__init__(message)


def _run_webcmd(args: list[str], stdin_data: str | None = None, timeout: int = 60) -> dict:
    """
    Thin subprocess wrapper around the real `webcmd` CLI.
    Raises WebcmdPoCError on non-zero exit OR on a well-formed
    {"error": {...}} response body (webcmd can return that with exit code 0
    in some paths, so we check the body shape too, not just returncode).
    """
    try:
        proc = subprocess.run(
            ["webcmd", *args],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise WebcmdPoCError(f"webcmd {' '.join(args)} timed out after {timeout}s") from e
    except FileNotFoundError as e:
        raise WebcmdPoCError("webcmd CLI not found on PATH — is it installed? (npm install -g @agentrhq/webcmd)") from e

    stdout = proc.stdout.strip()
    parsed: dict | None = None
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = None  # some subcommands (e.g. session close) return plain text, not JSON

    if isinstance(parsed, dict) and "error" in parsed:
        err = parsed["error"]
        raise WebcmdPoCError(err.get("message", str(err)), code=err.get("code"), raw=parsed)

    if proc.returncode != 0:
        raise WebcmdPoCError(
            f"webcmd {' '.join(args)} exited {proc.returncode}: {proc.stderr.strip() or stdout}"
        )

    return parsed if parsed is not None else {"raw_output": stdout}


def run_browser_proof_of_concept(test_url: str = DEFAULT_TEST_URL) -> dict:
    """
    The full minimal pipeline: create a session, navigate to a harmless
    test page, take an accessibility snapshot, close the session.
    Session close is always attempted even if navigation/snapshot fail,
    so we don't leak browser sessions across failed test runs.
    """
    session = _run_webcmd(["session", "create", "-f", "json"])
    session_id = session.get("id")
    if not session_id:
        raise WebcmdPoCError(f"Could not find 'id' field in session create output: {session}")

    navigate_result = None
    snapshot_result = None
    error: str | None = None

    try:
        navigate_script = f"await page.goto('{test_url}'); return await page.title();"
        navigate_result = _run_webcmd(
            ["--session", session_id, "browser", "run", "--stdin"],
            stdin_data=navigate_script,
            timeout=45,
        )
        snapshot_result = _run_webcmd(
            ["--session", session_id, "browser", "snapshot"],
            timeout=30,
        )
    except WebcmdPoCError as e:
        error = str(e)
    finally:
        try:
            _run_webcmd(["session", "close", session_id], timeout=15)
        except WebcmdPoCError:
            pass  # best-effort cleanup only; don't mask the real result/error above

    if error:
        raise WebcmdPoCError(error)

    return {
        "session_id": session_id,
        "test_url": test_url,
        "navigate_result": navigate_result,
        "snapshot": snapshot_result,
    }
