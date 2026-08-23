import json
import shutil
import subprocess
import time

from ingestion.result_parser import parse_result_text

VTU_URL = "https://result.vtudeveloper.in/"


class LiveResultError(Exception):
    pass


def run_webcmd(
    args: list[str],
    stdin_data: str | None = None,
    timeout: int = 60,
) -> dict:

    webcmd = shutil.which("webcmd")

    if not webcmd:
        raise LiveResultError("webcmd was not found on PATH")

    try:
        process = subprocess.run(
            [webcmd, *args],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise LiveResultError("Webcmd command timed out")

    output = process.stdout.strip()

    if process.returncode != 0:
        raise LiveResultError(
            process.stderr.strip() or output
        )

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"raw_output": output}


def fetch_result(usn: str) -> dict:

    # -----------------------------
    # 1. Create browser session
    # -----------------------------

    session = run_webcmd(
        ["session", "create", "-f", "json"]
    )

    session_id = session.get("id")

    if not session_id:
        raise LiveResultError(
            f"Could not create Webcmd session: {session}"
        )

    try:

        # -----------------------------
        # 2. Open VTU result portal
        # -----------------------------

        navigate_script = (
            f"await page.goto('{VTU_URL}'); "
            "return await page.title();"
        )

        run_webcmd(
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

        # -----------------------------
        # 3. Enter USN
        # -----------------------------

        fill_script = f"""
const input = page.getByRole(
    "textbox",
    {{name: "University Seat Number (USN)"}}
);

await input.fill("{usn}");

return await input.inputValue();
"""

        run_webcmd(
            [
                "--session",
                session_id,
                "browser",
                "run",
                "--stdin",
            ],
            stdin_data=fill_script,
            timeout=30,
        )

        # -----------------------------
        # 4. Click Search
        # -----------------------------

        click_script = """
await page.getByRole(
    "button",
    {name: "Search"}
).click();

return true;
"""

        run_webcmd(
            [
                "--session",
                session_id,
                "browser",
                "run",
                "--stdin",
            ],
            stdin_data=click_script,
            timeout=45,
        )

        # -----------------------------
        # 5. Wait for result page
        # -----------------------------

        time.sleep(2)

        # -----------------------------
        # 6. Extract visible result text
        # -----------------------------

        text_script = """
return await page.locator("body").innerText();
"""

        result_page = run_webcmd(
            [
                "--session",
                session_id,
                "browser",
                "run",
                "--stdin",
            ],
            stdin_data=text_script,
            timeout=30,
        )

        raw_text = result_page.get("result", "")

        if not raw_text:
            raise LiveResultError(
                "Webcmd returned an empty result page"
            )

        # -----------------------------
        # 7. Parse result
        # -----------------------------

        parsed = parse_result_text(raw_text)

        # Make sure we actually got the requested USN.
        if parsed.get("usn") != usn:
            raise LiveResultError(
                f"Returned USN {parsed.get('usn')} "
                f"does not match requested USN {usn}"
            )

        return parsed

    finally:

        # -----------------------------
        # 8. Always close browser session
        # -----------------------------

        try:
            run_webcmd(
                [
                    "session",
                    "close",
                    session_id,
                ],
                timeout=15,
            )
        except Exception:
            pass