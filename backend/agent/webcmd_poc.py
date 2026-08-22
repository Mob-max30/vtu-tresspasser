"""
SMALLEST POSSIBLE PROOF OF CONCEPT that this backend can genuinely invoke
Webcmd 0.7.4 and control a browser.

Pipeline:
    FastAPI endpoint
        -> webcmd 0.7.4
        -> browser session
        -> open harmless test webpage
        -> browser snapshot
        -> close session
        -> return result
"""

import json
import shutil
import subprocess

DEFAULT_TEST_URL = "https://example.com"


class WebcmdPoCError(Exception):
    """Raised whenever a Webcmd invocation fails."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        raw: dict | None = None,
    ):
        self.code = code
        self.raw = raw
        super().__init__(message)


def _run_webcmd(
    args: list[str],
    stdin_data: str | None = None,
    timeout: int = 60,
) -> dict:
    """
    Run the Webcmd CLI.

    Uses shutil.which() so Windows can correctly resolve the npm-installed
    webcmd.cmd executable.
    """

    webcmd = shutil.which("webcmd")

    if not webcmd:
        raise WebcmdPoCError(
            "webcmd CLI not found on PATH. "
            "Run `where.exe webcmd` to verify the installation."
        )

    try:
        proc = subprocess.run(
            [webcmd, *args],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )

    except subprocess.TimeoutExpired as e:
        raise WebcmdPoCError(
            f"webcmd {' '.join(args)} timed out after {timeout}s"
        ) from e

    except FileNotFoundError as e:
        raise WebcmdPoCError(
            f"Resolved Webcmd executable could not be started: {webcmd}"
        ) from e

    stdout = proc.stdout.strip()

    parsed: dict | None = None

    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = None

    # Webcmd can sometimes return an error object with exit code 0.
    if isinstance(parsed, dict) and "error" in parsed:
        err = parsed["error"]

        raise WebcmdPoCError(
            err.get("message", str(err)),
            code=err.get("code"),
            raw=parsed,
        )

    if proc.returncode != 0:
        raise WebcmdPoCError(
            f"webcmd {' '.join(args)} exited with code "
            f"{proc.returncode}: "
            f"{proc.stderr.strip() or stdout}"
        )

    return (
        parsed
        if parsed is not None
        else {"raw_output": stdout}
    )


def run_browser_proof_of_concept(
    test_url: str = DEFAULT_TEST_URL,
) -> dict:
    """
    Full Webcmd infrastructure test:

        1. Create Webcmd session
        2. Navigate to test URL
        3. Take browser snapshot
        4. Close session
        5. Return results
    """

    # ---------------------------------------------------------
    # 1. CREATE SESSION
    # ---------------------------------------------------------

    session = _run_webcmd(
        ["session", "create", "-f", "json"]
    )

    session_id = session.get("id")

    if not session_id:
        raise WebcmdPoCError(
            "Could not find 'id' field in Webcmd session "
            f"create output: {session}"
        )

    navigate_result = None
    snapshot_result = None
    error: str | None = None

    try:
        # -----------------------------------------------------
        # 2. NAVIGATE
        # -----------------------------------------------------

        navigate_script = (
            f"await page.goto('{test_url}'); "
            "return await page.title();"
        )

        navigate_result = _run_webcmd(
            [
                "--session",
                session_id,
                "browser",
                "run",
                "--stdin",
            ],
            stdin_data=navigate_script,
            timeout=45,
        )

        # -----------------------------------------------------
        # 3. SNAPSHOT
        # -----------------------------------------------------

        snapshot_result = _run_webcmd(
            [
                "--session",
                session_id,
                "browser",
                "snapshot",
            ],
            timeout=30,
        )

    except WebcmdPoCError as e:
        error = str(e)

    finally:
        # -----------------------------------------------------
        # 4. CLOSE SESSION
        # -----------------------------------------------------

        try:
            _run_webcmd(
                [
                    "session",
                    "close",
                    session_id,
                ],
                timeout=15,
            )
        except WebcmdPoCError:
            # Cleanup failure should not hide the original error.
            pass

    if error:
        raise WebcmdPoCError(error)

    # ---------------------------------------------------------
    # 5. RETURN RESULT
    # ---------------------------------------------------------

    return {
        "session_id": session_id,
        "test_url": test_url,
        "navigate_result": navigate_result,
        "snapshot": snapshot_result,
    }