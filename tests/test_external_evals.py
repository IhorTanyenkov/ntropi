"""External evaluation runs: exact payload receipts, Horizon import methods and the
generic ExternalHarness (fresh verified sessions, durable checkpoints, no feedback)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

import ntropi
from ntropi.evals import (
    SCHEMA,
    ExternalHarness,
    UnresolvedDispatch,
    session_log_verifier,
    visible_text,
)

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


# ── dispatch boundary: at most one outbound POST per case and run ──────────────



class _Counter:
    """A fake exact-send that counts every outbound POST."""

    def __init__(self, fail_after_send: BaseException | None = None) -> None:
        self.sent: list[bytes] = []
        self.fail_after_send = fail_after_send

    def __call__(self, body: bytes) -> ntropi.HTTPReceipt:
        self.sent.append(body)
        if self.fail_after_send is not None:
            raise self.fail_after_send
        return ntropi.HTTPReceipt("POST", "u", body, 200,
                                  json.dumps(_completion(f"s-{len(self.sent)}", "{}")).encode())


def _grade(case, receipt):
    return {"original": {"passed": receipt.ok}}


GRADED = dict(SUITE, grades=[{"name": "original"}])


def _h(tmp_path: Path, send, **kw) -> ExternalHarness:
    return ExternalHarness(suite=GRADED, run_id="run-1", send=send, grade=_grade,
                           checkpoint_dir=tmp_path / "ckpt", **kw)


def test_an_interrupted_dispatch_is_never_resent(tmp_path: Path) -> None:
    crash = _Counter(fail_after_send=KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        _h(tmp_path, crash).run(statement="x")
    assert len(crash.sent) == 1
    resumed = _Counter()
    harness = _h(tmp_path, resumed)
    with pytest.raises(UnresolvedDispatch) as err:
        harness.run(statement="resume")
    assert err.value.cases == ["c1"]
    assert len(resumed.sent) == 1, "only the unsent case c2 goes out"
    assert json.loads(resumed.sent[0]) == SUITE["cases"][1]["request"]
    assert harness.pending() == ["c1"]
    with pytest.raises(UnresolvedDispatch):
        _h(tmp_path, resumed).run(statement="again")
    assert len(resumed.sent) == 1


def test_a_receipt_that_cannot_be_saved_leaves_the_case_unknown(tmp_path: Path, monkeypatch) -> None:
    from ntropi import evals

    real = evals._write
    calls = {"n": 0}

    def flaky(path, data):
        if path.name == "receipt.json" and calls["n"] == 0:
            calls["n"] += 1
            raise OSError("disk full")
        real(path, data)

    monkeypatch.setattr(evals, "_write", flaky)
    sender = _Counter()
    with pytest.raises(OSError):
        _h(tmp_path, sender).run(statement="x")
    monkeypatch.setattr(evals, "_write", real)
    with pytest.raises(UnresolvedDispatch):
        _h(tmp_path, sender).run(statement="resume")
    assert [json.loads(b) for b in sender.sent] == [SUITE["cases"][0]["request"], SUITE["cases"][1]["request"]]


def test_concurrent_resumes_send_each_case_once(tmp_path: Path) -> None:
    import threading

    gate = threading.Event()
    sender = _Counter()

    def slow(body: bytes):
        gate.wait(5)
        return sender(body)

    outcomes: list[str] = []

    def worker():
        try:
            _h(tmp_path, slow).run(statement="x")
            outcomes.append("complete")
        except UnresolvedDispatch:
            outcomes.append("unresolved")

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    gate.set()
    for t in threads:
        t.join()
    assert len(sender.sent) == 2, "two cases, one POST each across four concurrent runs"
    assert len({b for b in sender.sent}) == 2


def test_adopt_and_abandon_resolve_without_sending(tmp_path: Path) -> None:
    crash = _Counter(fail_after_send=RuntimeError("lost connection after send"))
    with pytest.raises(RuntimeError):
        _h(tmp_path, crash).run(statement="x")
    sender = _Counter()
    harness = _h(tmp_path, sender, cases=["c1"])
    with pytest.raises(ValueError):
        harness.adopt("c1", status=200, response_body=b"{}", note=" ")
    harness.adopt("c1", status=200, response_body=json.dumps(_completion("s-r", "{}")).encode(),
                  note="recovered from the node's session log")
    record = harness.run(statement="adopted")
    row = record["cases"][0]
    assert sender.sent == []
    assert row["evidence"]["dispatch_state"] == "adopted"
    assert row["session_id"] is None, "no log verifier: the session is not claimed"
    assert row["metrics"]["request_elapsed_s"] is None

    crash2 = _Counter(fail_after_send=RuntimeError("killed"))
    with pytest.raises(RuntimeError):
        ExternalHarness(suite=GRADED, run_id="run-2", send=crash2, grade=_grade,
                        checkpoint_dir=tmp_path / "ckpt", cases=["c2"]).run(statement="x")
    second = ExternalHarness(suite=GRADED, run_id="run-2", send=sender, grade=_grade,
                             checkpoint_dir=tmp_path / "ckpt", cases=["c2"])
    with pytest.raises(ValueError):
        second.abandon("c1", reason="not dispatched")
    second.abandon("c2", reason="process killed during dispatch")
    row = second.run(statement="abandoned")["cases"][0]
    assert sender.sent == []
    assert row["grades"] == {"original": {"passed": None}}
    assert row["http_status"] is None and row["session_id"] is None
    assert row["error"].startswith("dispatch outcome unknown")


@pytest.mark.parametrize("bad", ["../escape", "..\\escape", "a/b", "a\\b", "/abs", "C:evil", ".hidden", "", None])
def test_unsafe_case_ids_are_refused_before_anything_is_written(tmp_path: Path, bad) -> None:
    suite = dict(GRADED, cases=[{"id": bad, "request": {"model": "nbot"}}])
    sender = _Counter()
    with pytest.raises(ValueError):
        ExternalHarness(suite=suite, run_id="run-1", send=sender, grade=_grade, checkpoint_dir=tmp_path / "ckpt")
    assert sender.sent == [] and not (tmp_path / "ckpt").exists()


def test_run_case_is_bound_to_the_pinned_suite(tmp_path: Path) -> None:
    sender = _Counter()
    harness = _h(tmp_path, sender)
    with pytest.raises(ValueError):
        harness.run_case({"id": "c1", "request": {"model": "nbot", "messages": [], "temperature": 1}})
    with pytest.raises(ValueError):
        harness.run_case({"id": "c9", "request": SUITE["cases"][0]["request"]})
    with pytest.raises(ValueError):
        harness.run_case({"id": "../c1", "request": SUITE["cases"][0]["request"]})
    with pytest.raises(ValueError):
        ExternalHarness(suite=GRADED, run_id="run-1", send=sender, grade=_grade,
                        checkpoint_dir=tmp_path / "ckpt", cases=["zz"])
    with pytest.raises(ValueError):
        ExternalHarness(suite=dict(GRADED, definition_sha256="yes"), run_id="run-1", send=sender,
                        grade=_grade, checkpoint_dir=tmp_path / "ckpt")
    assert sender.sent == []
    assert harness.run_case({"id": "c1"})["grades"]["original"]["passed"] is True
    assert len(sender.sent) == 1


def test_symlinked_checkpoints_are_refused(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "ckpt").mkdir()
    (tmp_path / "ckpt" / "run-1").mkdir()
    (tmp_path / "ckpt" / "run-1" / "c1").symlink_to(outside, target_is_directory=True)
    sender = _Counter()
    with pytest.raises(ValueError):
        _h(tmp_path, sender).run_case("c1")
    assert sender.sent == [] and list(outside.iterdir()) == []
    (tmp_path / "linked").symlink_to(tmp_path / "ckpt", target_is_directory=True)
    with pytest.raises(ValueError):
        ExternalHarness(suite=GRADED, run_id="run-1", send=sender, grade=_grade, checkpoint_dir=tmp_path / "linked")
