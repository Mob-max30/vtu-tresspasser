"""
These tests mock subprocess.run rather than actually launching a browser —
CI/sandboxed environments can't reliably run a headed browser. The mocked
responses are copied verbatim from REAL webcmd 0.7.4 output captured
during live manual testing (see agent/webcmd_poc.py's module docstring),
so this tests our parsing/error-handling logic against real shapes, not
invented ones.
"""

import json
from unittest.mock import patch, MagicMock

import pytest
from agent.webcmd_poc import run_browser_proof_of_concept, WebcmdPoCError

REAL_SESSION_CREATE_OUTPUT = json.dumps({
    "id": "session_3a2210db-a15f-42c5-9cf6-938ad7d3adde",
    "kind": "explicit",
})

REAL_BROWSER_RUN_OUTPUT = json.dumps({
    "ok": True,
    "result": "",
    "logs": [],
    "page": {"id": "page-1787377984777-2", "url": "https://example.com/", "title": ""},
    "snapshotDiff": "<page ...>...</page>",
    "artifacts": [],
    "warnings": [],
    "limits": {"outputTruncated": False, "snapshotTruncated": False},
    "timings": {"quickjs_boot_ms": 114, "program_ms": 288},
})

REAL_SNAPSHOT_OUTPUT = json.dumps({
    "ok": True,
    "tree": "<page title=\"https://example.com/\" url=\"https://example.com/\">...</page>",
    "page": {"id": "page-1787377984777-2", "url": "https://example.com/", "title": ""},
    "warnings": [],
    "limits": {"snapshotTruncated": True},
})

REAL_SESSION_CLOSE_OUTPUT = "closed: true\nalreadyIdle: false\nsession: session_3a2210db-..."

REAL_ERROR_OUTPUT = json.dumps({
    "error": {
        "code": "runtime_command_failed",
        "message": "browserType.launchPersistentContext: Missing X server or $DISPLAY",
    }
})


def _mock_result(stdout, returncode=0):
    m = MagicMock()
    m.stdout = stdout
    m.stderr = ""
    m.returncode = returncode
    return m


def test_full_success_pipeline():
    """Happy path, using the exact JSON shapes captured from a real run."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            _mock_result(REAL_SESSION_CREATE_OUTPUT),
            _mock_result(REAL_BROWSER_RUN_OUTPUT),
            _mock_result(REAL_SNAPSHOT_OUTPUT),
            _mock_result(REAL_SESSION_CLOSE_OUTPUT),
        ]
        result = run_browser_proof_of_concept("https://example.com")

    assert result["session_id"] == "session_3a2210db-a15f-42c5-9cf6-938ad7d3adde"
    assert result["navigate_result"]["ok"] is True
    assert result["snapshot"]["ok"] is True
    assert mock_run.call_count == 4  # create, run, snapshot, close


def test_session_create_missing_id_field_raises():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_mock_result(json.dumps({"kind": "explicit"}))]  # no "id"
        with pytest.raises(WebcmdPoCError, match="Could not find 'id'"):
            run_browser_proof_of_concept()


def test_navigate_failure_still_closes_session_and_raises():
    """Real regression check: a captured runtime_command_failed error (e.g.
    the actual 'Missing X server' error we hit) must surface as a
    WebcmdPoCError AND session close must still be attempted."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            _mock_result(REAL_SESSION_CREATE_OUTPUT),
            _mock_result(REAL_ERROR_OUTPUT),          # navigate fails
            _mock_result(REAL_SESSION_CLOSE_OUTPUT),  # cleanup still runs
        ]
        with pytest.raises(WebcmdPoCError, match="Missing X server"):
            run_browser_proof_of_concept()

        assert mock_run.call_count == 3  # create, failed run, close (no snapshot attempted)


def test_nonzero_exit_without_json_body_raises():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            _mock_result(REAL_SESSION_CREATE_OUTPUT),
            _mock_result("", returncode=1),  # crash with no parseable output at all
            _mock_result(REAL_SESSION_CLOSE_OUTPUT),
        ]
        with pytest.raises(WebcmdPoCError):
            run_browser_proof_of_concept()
