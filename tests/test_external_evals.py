"""External evaluation runs: exact payload receipts, Horizon import methods and the
generic ExternalHarness (fresh verified sessions, durable checkpoints, no feedback)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

import ntropi
from ntropi.evals import SCHEMA, ExternalHarness, session_log_verifier, visible_text

SUITE = {
    "schema": SCHEMA,
    "id": "su-sample",
    "dataset_role": "development_regression",
    "definition_sha256": "d" * 64,
    "cases": [
        {"id": "c1", "request": {"model": "nbot", "messages": [{"role": "user", "content": "one"}],
                                 "temperature": 0}},
        {"id": "c2", "request": {"model": "nbot", "messages": [{"role": "user", "content": "two"}],
                                 "temperature": 0}},
    ],
}


def _completion(session: str, content: str) -> dict:
    return {"id": f"chatcmpl-{session}",
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}}


@respx.mock
def test_send_exact_posts_the_body_unchanged_and_keeps_an_error_status() -> None:
    route = respx.post("http://n/v1/chat/completions").mock(
        side_effect=[httpx.Response(500, json={"error": "boom"}),
                     httpx.Response(200, json=_completion("s-1", "{}"))])
    client = ntropi.nbot.Client("http://n")
    body = json.dumps(SUITE["cases"][0]["request"]).encode()
    failed = client.chat.completions.send_exact(body)
    assert failed.status == 500 and not failed.ok
    assert failed.json() == {"error": "boom"}
    assert route.call_count == 1, "a POST is never replayed"
    assert route.calls[0].request.content == body
    assert "stream" not in json.loads(route.calls[0].request.content)
    ok = client.chat.completions.send_exact(body)
    assert ok.status == 200 and ok.json()["id"] == "chatcmpl-s-1"
    assert ok.elapsed_s >= 0


@respx.mock
def test_send_exact_reports_a_transport_failure_as_a_receipt() -> None:
    respx.post("http://n/v1/chat/completions").mock(side_effect=httpx.ConnectError("down"))
    receipt = ntropi.nbot.Client("http://n").chat.completions.send_exact(b"{}")
    assert receipt.status is None and receipt.error and receipt.error.startswith("connection")


@respx.mock
def test_horizon_import_methods_and_conflict() -> None:
    respx.post("http://h/api/suites/import").mock(
        return_value=httpx.Response(200, json={"status": "unchanged", "record": {"id": "su-sample"}}))
    respx.post("http://h/api/suites/su-sample/runs/import").mock(
        return_value=httpx.Response(409, json={"status": "conflict", "error": "different content"}))
    respx.get("http://h/api/suites/su-sample/runs/run-1").mock(
        return_value=httpx.Response(200, json={"run_id": "run-1", "cases": []}))
    h = ntropi.horizon.Client("http://h", key="k")
    assert h.suites.import_suite({"id": "su-sample"})["status"] == "unchanged"
    with pytest.raises(ntropi.ConflictError):
        h.suites.import_run("su-sample", {"run_id": "run-1"})
    assert h.suites.get_run("su-sample", "run-1")["run_id"] == "run-1"


@pytest.mark.asyncio
@respx.mock
async def test_async_import_and_exact_send() -> None:
    respx.post("http://h/api/suites/su-sample/runs/import").mock(
        return_value=httpx.Response(201, json={"status": "created", "record": {"run_id": "r"}}))
    route = respx.post("http://n/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_completion("s-9", "x")))
    async with ntropi.horizon.AsyncClient("http://h", key="k") as h:
        assert (await h.suites.import_run("su-sample", {"run_id": "r"}))["status"] == "created"
    async with ntropi.nbot.AsyncClient("http://n") as n:
        receipt = await n.chat.completions.send_exact(b'{"a":1}')
    assert receipt.status == 200 and route.calls[0].request.content == b'{"a":1}'


def test_visible_text_drops_inline_reasoning() -> None:
    assert visible_text("<think>private</think>{\"a\":1}") == '{"a":1}'
    assert visible_text(None) is None


def _harness(tmp_path: Path, send, logs: Path | None = None, run_id: str = "run-1") -> ExternalHarness:
    def grade(case, receipt):
        doc = receipt.json() or {}
        text = (doc.get("choices") or [{}])[0].get("message", {}).get("content")
        return {"original": {"passed": text == "{}" if receipt.ok else False}}

    return ExternalHarness(suite=SUITE, run_id=run_id, send=send, grade=grade,
                           checkpoint_dir=tmp_path / "ckpt",
                           verify_session=session_log_verifier(logs) if logs else None)


@respx.mock
def test_harness_sends_each_case_once_with_fresh_verified_sessions_and_no_feedback(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "s-a.jsonl").write_text("")
    (logs / "s-b.jsonl").write_text("")
    chat = respx.post("http://n/v1/chat/completions").mock(
        side_effect=[httpx.Response(200, json=_completion("s-a", "{}")),
                     httpx.Response(500, json={"error": "upstream"})])
    anything_else = respx.route(method__in=["GET", "POST", "PUT", "PATCH", "DELETE"]).mock(
        return_value=httpx.Response(599))
    client = ntropi.nbot.Client("http://n")
    record = _harness(tmp_path, client.chat.completions.send_exact, logs).run(statement="smoke")

    assert chat.call_count == 2 and anything_else.call_count == 0
    assert [json.loads(c.request.content) for c in chat.calls] == [c["request"] for c in SUITE["cases"]]
    first, second = record["cases"]
    assert first["session_id"] == "s-a" and first["session_ids"] == ["s-a"]
    assert first["grades"]["original"]["passed"] is True
    assert second["http_status"] == 500 and second["error"] == "HTTP 500"
    assert second["session_id"] is None and second["response_text"] is None
    assert record["evidence"]["class"] == "new_run"
    assert record["suite_definition_sha256"] == SUITE["definition_sha256"]
    assert second["metrics"]["usage"] is None


@respx.mock
def test_unverified_session_is_not_reported(tmp_path: Path) -> None:
    respx.post("http://n/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_completion("s-ghost", "{}")))
    client = ntropi.nbot.Client("http://n")
    case = _harness(tmp_path, client.chat.completions.send_exact, tmp_path).run_case(SUITE["cases"][0])
    assert case["session_id"] is None
    assert case["evidence"]["completion_id"] == "chatcmpl-s-ghost"
    assert case["evidence"]["session_verified"] is False


@respx.mock
def test_resume_never_resends_a_checkpointed_case(tmp_path: Path) -> None:
    chat = respx.post("http://n/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_completion("s-1", "{}")))
    client = ntropi.nbot.Client("http://n")
    _harness(tmp_path, client.chat.completions.send_exact).run(statement="first")
    _harness(tmp_path, client.chat.completions.send_exact).run(statement="resumed")
    assert chat.call_count == 2, "two cases, each sent once across both invocations"
    other = dict(SUITE, definition_sha256="e" * 64)
    with pytest.raises(ValueError):
        ExternalHarness(suite=other, run_id="run-1", send=client.chat.completions.send_exact,
                        grade=lambda c, r: {}, checkpoint_dir=tmp_path / "ckpt").run(statement="x")


def test_two_runs_use_separate_checkpoints(tmp_path: Path) -> None:
    sent: list[bytes] = []

    def send(body: bytes):
        sent.append(body)
        return ntropi.HTTPReceipt("POST", "u", body, 200,
                                  json.dumps(_completion(f"s-{len(sent)}", "{}")).encode())

    a = _harness(tmp_path, send, run_id="run-a").run(statement="a")
    b = _harness(tmp_path, send, run_id="run-b").run(statement="b")
    ids = [c["evidence"]["completion_id"] for c in a["cases"] + b["cases"]]
    assert len(sent) == 4 and len(set(ids)) == 4
    with pytest.raises(ValueError):
        _harness(tmp_path, send, run_id="../escape")
